import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import db, decisions, worker
from backend.decisions import Decision
from backend.main import INSTRUCTIONS

CLAIM = "CLM-1001"


def approval(payout: float) -> Decision:
    return Decision(
        decision="approve", payout=payout, reason="Covered.", policy_section="Section 3"
    )


def finish_queued_work() -> None:
    worker.executor.submit(lambda: None).result()


def claim(client: TestClient) -> dict:
    return client.get(f"/api/claims/{CLAIM}").json()


def last_step(client: TestClient) -> str:
    return client.get(f"/api/claims/{CLAIM}/steps").json()[-1]["text"]


def test_steps_are_listed_in_order(client: TestClient):
    for text in ("First", "Second"):
        response = client.post(
            f"/api/claims/{CLAIM}/steps", json={"thread_id": "t1", "text": text}
        )
        assert response.status_code == 200
    steps = client.get(f"/api/claims/{CLAIM}/steps").json()
    assert [s["text"] for s in steps] == ["First", "Second"]
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_instructions_are_served_read_only(client: TestClient):
    text = client.get("/api/instructions").json()["text"]
    assert text == INSTRUCTIONS.read_text(encoding="utf-8")
    assert "section 10" in text
    assert "manual" not in text.lower()
    assert client.put("/api/instructions", json={"text": "x"}).status_code == 405


def test_run_agent_queues_only_a_waiting_claim(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    ran: list[str] = []
    monkeypatch.setattr(worker, "run", lambda claim_id, _: ran.append(claim_id))
    response = client.post(f"/api/claims/{CLAIM}/agent-run")
    assert response.status_code == 202
    finish_queued_work()
    assert ran == [CLAIM]
    client.post(f"/api/claims/{CLAIM}/start")
    assert client.post(f"/api/claims/{CLAIM}/agent-run").status_code == 409
    assert client.post("/api/claims/CLM-9999/agent-run").status_code == 404


def test_work_queue_runs_every_waiting_claim_one_at_a_time_in_order(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    ran: list[str] = []
    running = threading.Semaphore(1)

    def stub_run(claim_id: str, _: str) -> None:
        assert running.acquire(blocking=False)
        ran.append(claim_id)
        running.release()

    monkeypatch.setattr(worker, "run", stub_run)
    client.post(f"/api/claims/{CLAIM}/start")
    response = client.post("/api/queue/agent-run")
    assert response.status_code == 202
    assert response.json() == {"started": 24}
    finish_queued_work()
    assert ran == [c["claim_id"] for c in client.get("/api/claims").json()][1:]


def test_a_failed_run_puts_the_claim_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def failing_run(claim_id: str, _: str) -> None:
        decisions.start_claim(claim_id)
        decisions.record_decision(claim_id, approval(400))
        raise RuntimeError("the model is down")

    monkeypatch.setattr(worker, "run", failing_run)
    worker.work_on(CLAIM)
    recorded = claim(client)
    assert recorded["status"] == "waiting"
    assert recorded["decision"] is None
    assert recorded["payment"] is None
    assert last_step(client) == (
        "The agent stopped before finishing: the model is down"
    )


@pytest.mark.parametrize(
    ("payout", "expected_status"),
    [(1500, "waiting_for_sign_off"), (400, "decided")],
)
def test_a_failure_after_the_decision_changes_nothing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    payout: float,
    expected_status: str,
):
    def failing_run(claim_id: str, _: str) -> None:
        decisions.start_claim(claim_id)
        decisions.record_decision(claim_id, approval(payout))
        if expected_status == "decided":
            decisions.pay_claim(claim_id, payout)
        raise RuntimeError("the model is down")

    monkeypatch.setattr(worker, "run", failing_run)
    worker.work_on(CLAIM)
    recorded = claim(client)
    assert recorded["status"] == expected_status
    assert recorded["decision"]["payout"] == payout
    assert client.get(f"/api/claims/{CLAIM}/steps").json() == []


def test_a_restart_puts_interrupted_claims_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "restart.db")
    db.setup()
    decisions.start_claim(CLAIM)
    decisions.record_decision(CLAIM, approval(400))
    db.setup()
    with db.reading() as connection:
        status = connection.execute(
            "SELECT status FROM claims WHERE claim_id = ?", (CLAIM,)
        ).fetchone()[0]
        decision_rows = connection.execute("SELECT COUNT(*) FROM decisions").fetchone()
    assert status == "waiting"
    assert decision_rows[0] == 0

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app

CLAIM = "CLM-1001"
DATA = Path(__file__).parents[2] / "data"


def decide(client: TestClient, decision: str, payout: float):
    return client.post(
        f"/api/claims/{CLAIM}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": "The wording covers this.",
            "policy_section": "Section 3: Trip Delay",
        },
    )


def approve(client: TestClient, payout: float):
    client.post(f"/api/claims/{CLAIM}/start")
    return decide(client, "approve", payout)


def pay(client: TestClient, amount: float):
    return client.post(f"/api/claims/{CLAIM}/payment", json={"amount": amount})


def sign_off(client: TestClient, handler_id: str = "HND-01"):
    return client.post(f"/api/claims/{CLAIM}/sign-off", json={"handler_id": handler_id})


def claim(client: TestClient) -> dict:
    return client.get(f"/api/claims/{CLAIM}").json()


def payment_rows() -> int:
    with db.reading() as connection:
        return connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0]


def test_start_moves_only_a_waiting_claim(client: TestClient):
    assert client.post(f"/api/claims/{CLAIM}/start").json() == {"status": "in_progress"}
    assert claim(client)["status"] == "in_progress"
    assert client.post(f"/api/claims/{CLAIM}/start").status_code == 409


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_and_refer_are_decided_with_no_payout(
    client: TestClient, decision: str
):
    client.post(f"/api/claims/{CLAIM}/start")
    assert decide(client, decision, 10).status_code == 422
    assert decide(client, decision, 0).json() == {"status": "decided"}
    assert claim(client)["decision"]["decision"] == decision


def test_a_payout_at_the_limit_needs_no_sign_off(client: TestClient):
    assert approve(client, 1000.00).json() == {"status": "in_progress"}
    assert pay(client, 1000.00).json() == {"status": "decided"}
    recorded = claim(client)
    assert recorded["status"] == "decided"
    assert recorded["payment"]["amount"] == 1000.00
    assert recorded["sign_off"] is None


def test_a_payout_one_cent_over_the_limit_waits_for_sign_off(client: TestClient):
    assert approve(client, 1000.01).json() == {"status": "waiting_for_sign_off"}


def test_a_zero_payout_approval_is_decided_with_no_payment(client: TestClient):
    assert approve(client, 0).json() == {"status": "decided"}
    assert payment_rows() == 0


def test_a_decision_needs_an_in_progress_claim(client: TestClient):
    assert decide(client, "approve", 100).status_code == 409
    approve(client, 1500)
    assert decide(client, "approve", 900).status_code == 409
    assert claim(client)["decision"]["payout"] == 1500


def test_paying_over_the_limit_without_sign_off_is_blocked(client: TestClient):
    approve(client, 1500)
    response = pay(client, 1500)
    assert response.status_code == 403
    assert "sign-off" in response.json()["detail"]
    assert payment_rows() == 0
    assert claim(client)["status"] == "waiting_for_sign_off"


def test_a_payment_must_match_the_approved_payout(client: TestClient):
    approve(client, 1500)
    assert pay(client, 900).status_code == 409
    assert payment_rows() == 0


def test_a_claim_is_paid_once(client: TestClient):
    approve(client, 400)
    assert pay(client, 400).status_code == 200
    assert pay(client, 400).status_code == 409
    assert payment_rows() == 1


def test_a_payment_needs_an_approved_decision(client: TestClient):
    assert pay(client, 100).status_code == 409
    client.post(f"/api/claims/{CLAIM}/start")
    decide(client, "decline", 0)
    assert pay(client, 100).status_code == 409
    assert payment_rows() == 0


def test_a_payment_on_an_unknown_claim_is_a_404(client: TestClient):
    response = client.post("/api/claims/CLM-9999/payment", json={"amount": 10})
    assert response.status_code == 404


def test_sign_off_records_the_handler_and_pays(client: TestClient):
    approve(client, 1500)
    assert sign_off(client).json() == {"status": "decided"}
    recorded = claim(client)
    assert recorded["status"] == "decided"
    assert recorded["sign_off"]["handler_name"] == "Dana Whitfield"
    assert recorded["payment"]["amount"] == 1500
    assert payment_rows() == 1


def test_sign_off_refuses_the_wrong_handler_or_claim(client: TestClient):
    assert sign_off(client).status_code == 409
    approve(client, 1500)
    assert sign_off(client, "HND-99").status_code == 404
    with db.transaction() as connection:
        connection.execute(
            "UPDATE handlers SET can_approve_over_limit = 0 WHERE handler_id = 'HND-02'"
        )
    assert sign_off(client, "HND-02").status_code == 403
    assert payment_rows() == 0


def test_simultaneous_payments_pay_once(client: TestClient):
    approve(client, 400)
    with ThreadPoolExecutor(8) as pool:
        codes = sorted(
            r.status_code for r in pool.map(lambda _: pay(client, 400), range(8))
        )
    assert codes == [200] + [409] * 7
    assert payment_rows() == 1


def test_simultaneous_sign_offs_pay_once(client: TestClient):
    approve(client, 1500)
    with ThreadPoolExecutor(8) as pool:
        codes = sorted(
            r.status_code for r in pool.map(lambda _: sign_off(client), range(8))
        )
    assert codes == [200] + [409] * 7
    assert payment_rows() == 1


def test_the_limit_comes_from_the_seed_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    seed_dir = tmp_path / "data"
    shutil.copytree(DATA, seed_dir, ignore=shutil.ignore_patterns("evals", "security"))
    company = json.loads((seed_dir / "company.json").read_text())
    company["payout_approval_limit"] = 500.0
    (seed_dir / "company.json").write_text(json.dumps(company))
    monkeypatch.setattr(db, "DATA_DIR", seed_dir)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "limit.db")
    with TestClient(app) as client:
        assert approve(client, 600).json() == {"status": "waiting_for_sign_off"}

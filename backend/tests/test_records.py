import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app

DATA = Path(__file__).parents[2] / "data"
ANSWER_KEY_FIELDS = {
    "difficulty",
    "failure_class",
    "tone",
    "tiny",
    "needs",
    "over_approval_limit",
}


def keys_in(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_in(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_in(v)}
    return set()


def test_queue_holds_exactly_the_seeded_claims(client: TestClient):
    seeded = [c["claim_id"] for c in json.loads((DATA / "claims.json").read_text())]
    queue = client.get("/api/claims").json()
    assert [c["claim_id"] for c in queue] == seeded
    assert len(queue) == 25
    assert {c["status"] for c in queue} == {"waiting"}
    assert queue[0] == {
        "claim_id": "CLM-1001",
        "customer_name": "Maya Patel",
        "claim_type": "trip_delay",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "status": "waiting",
    }


def test_claim_is_returned_in_full(client: TestClient):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["amount_claimed"] == 420.0
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4


@pytest.mark.parametrize(
    "path",
    [
        "/api/claims/CLM-9999",
        "/api/claims/CLM-1901",
        "/api/policies/POL-9999",
        "/api/customers/CUS-9999",
    ],
)
def test_unknown_records_return_404(client: TestClient, path: str):
    assert client.get(path).status_code == 404


def test_policy_includes_its_plan_limits(client: TestClient):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["plan_details"]["per_item_limit"] == 300.0
    assert policy["plan_details"]["deductible"] == 50.0


def test_policy_includes_its_add_ons(client: TestClient):
    with_add_on = next(
        p
        for p in json.loads((DATA / "policies.json").read_text())
        if "electronics_plus" in p["add_ons"]
    )
    policy = client.get(f"/api/policies/{with_add_on['policy_id']}").json()
    assert 1200.0 in [
        a.get("electronics_per_item_limit") for a in policy["add_on_details"]
    ]


def test_customer_has_history_and_no_contact_details(client: TestClient):
    customer = client.get("/api/customers/CUS-3001").json()
    assert customer == {
        "customer_id": "CUS-3001",
        "name": "Maya Patel",
        "customer_since": "2023-04-11",
        "previous_claims": customer["previous_claims"],
    }
    assert customer["previous_claims"][0]["claim_id"] == "CLM-0412"


def test_policy_wording_and_handlers(client: TestClient):
    wording = client.get("/api/policy-wording").json()["text"]
    assert wording.startswith("# UnderCover Travel Insurance: Policy Wording")
    handlers = client.get("/api/handlers").json()
    assert len(handlers) == 3
    assert handlers[0]["can_approve_over_limit"] is True
    assert "email" not in handlers[0]


def test_seed_keeps_existing_data_on_restart(client: TestClient):
    with db.transaction() as connection:
        connection.execute("UPDATE claims SET status = 'decided'")
    db.setup()
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert len(client.get("/api/claims").json()) == 25


def test_seed_needs_only_its_listed_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    assert db.SEED_FILES == (
        "claims.json",
        "company.json",
        "customers.json",
        "handlers.json",
        "plans.json",
        "policies.json",
    )
    seed_dir = tmp_path / "data"
    seed_dir.mkdir()
    for name in db.SEED_FILES:
        shutil.copy(DATA / name, seed_dir / name)
    monkeypatch.setattr(db, "DATA_DIR", seed_dir)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "seed.db")
    db.setup()
    with db.reading() as connection:
        assert connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 25


def test_no_response_carries_the_answer_key(client: TestClient):
    responses = [
        client.get("/api/claims").json(),
        client.get("/api/claims/CLM-1001").json(),
        client.get("/api/policies/POL-2001").json(),
        client.get("/api/customers/CUS-3001").json(),
    ]
    assert not keys_in(responses) & ANSWER_KEY_FIELDS


def test_every_operation_is_documented_with_no_optional_inputs():
    schema = app.openapi()
    components = schema["components"]["schemas"]
    for operations in schema["paths"].values():
        for operation in operations.values():
            assert operation["operationId"]
            assert operation["summary"]
            assert "\n" not in operation["description"]
            assert all(p["required"] for p in operation.get("parameters", []))
            if "requestBody" in operation:
                assert operation["requestBody"]["required"]
                body = operation["requestBody"]["content"]["application/json"]
                name = body["schema"]["$ref"].rsplit("/", 1)[-1]
                body_schema = components[name]
                assert set(body_schema["properties"]) == set(body_schema["required"])

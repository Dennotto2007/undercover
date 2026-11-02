from collections.abc import Iterator
from contextlib import nullcontext
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend import db, worker
from backend.main import app

CLAIM = "CLM-1001"


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_reply(*calls: tuple[str, dict]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": str(i)}
            for i, (name, args) in enumerate(calls)
        ],
    )


def decision(kind: str, payout: float) -> tuple[str, dict]:
    return (
        "record_decision",
        {
            "claim_id": CLAIM,
            "decision": kind,
            "payout": payout,
            "reason": "The wording covers this.",
            "policy_section": "Section 3: Trip Delay",
        },
    )


def pay(amount: float) -> tuple[str, dict]:
    return ("pay_claim", {"claim_id": CLAIM, "amount": amount})


def stub(*replies: AIMessage) -> StubModel:
    return StubModel(messages=iter(replies))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(main, "backend", lambda: nullcontext(TestClient(app)))
    with TestClient(app) as test_client:
        yield test_client


def claim(client: TestClient) -> dict:
    return client.get(f"/api/claims/{CLAIM}").json()


def steps(client: TestClient) -> list[str]:
    return [s["text"] for s in client.get(f"/api/claims/{CLAIM}/steps").json()]


def test_the_agent_has_exactly_these_tools():
    assert [t.name for t in main.TOOLS] == [
        "get_claim",
        "get_policy",
        "get_customer",
        "get_policy_wording",
        "record_decision",
        "pay_claim",
    ]


def test_run_works_a_claim_through_to_payment(client: TestClient):
    reply = main.run(
        CLAIM,
        "thread-1",
        stub(
            tool_reply(("get_claim", {"claim_id": CLAIM})),
            tool_reply(
                ("get_policy", {"policy_id": "POL-2001"}),
                ("get_customer", {"customer_id": "CUS-3001"}),
                ("get_policy_wording", {}),
            ),
            tool_reply(decision("approve", 420)),
            tool_reply(pay(420)),
            AIMessage(content="Approved and paid."),
        ),
    )
    assert reply == "Approved and paid."
    recorded = claim(client)
    assert recorded["status"] == "decided"
    assert recorded["decision"]["reason"] == "The wording covers this."
    assert recorded["payment"]["amount"] == 420
    assert steps(client) == [
        "Reading the claim",
        "Reading the policy",
        "Reading the customer's claim history",
        "Reading the policy wording",
        "Recording the decision: approve, $420.00",
        "Paying $420.00",
        "Approved and paid.",
    ]


def test_the_agent_cannot_pay_over_the_limit_even_if_it_tries(client: TestClient):
    main.run(
        CLAIM,
        "thread-1",
        stub(
            tool_reply(decision("approve", 1500)),
            tool_reply(pay(1500)),
            AIMessage(content="I could not pay."),
        ),
    )
    recorded = claim(client)
    assert recorded["status"] == "waiting_for_sign_off"
    assert recorded["payment"] is None
    assert any("Payment blocked" in step for step in steps(client))


def test_a_refusal_reaches_the_model_as_the_tool_result(client: TestClient):
    reply = main.pay_claim.invoke({"claim_id": CLAIM, "amount": 100})
    assert reply == f"{main.REFUSED}{CLAIM} has no approved decision"


def test_run_stops_if_the_claim_is_not_waiting(client: TestClient):
    client.post(f"/api/claims/{CLAIM}/start")
    with pytest.raises(Exception, match="409"):
        main.run(CLAIM, "thread-1", stub(AIMessage(content="Never reached.")))


@pytest.mark.parametrize(
    "replies",
    [
        [AIMessage(content="I have nothing to record.")],
        [
            tool_reply(decision("approve", 400)),
            tool_reply(pay(300)),
            AIMessage(content="The payment was refused."),
        ],
    ],
    ids=["no decision", "refused payment"],
)
def test_an_unfinished_run_puts_the_claim_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, replies: list[AIMessage]
):
    monkeypatch.setattr(worker, "run", lambda c, t: main.run(c, t, stub(*replies)))
    worker.work_on(CLAIM)
    recorded = claim(client)
    assert recorded["status"] == "waiting"
    assert recorded["decision"] is None
    assert recorded["payment"] is None
    assert steps(client)[-1] == (
        "The agent stopped before finishing: "
        "the run ended before the claim was finished"
    )


def test_model_name_and_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    assert main.model().request_timeout == 120
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"

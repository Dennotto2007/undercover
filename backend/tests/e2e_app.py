"""The real app and agent for Playwright, with a stub model and a temporary database."""

import tempfile
import time
from pathlib import Path

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main as agent
from backend import db, worker
from backend.main import app

__all__ = ["app"]

BACKEND_URL = "http://127.0.0.1:8001"
SECONDS_PER_REPLY = 0.3


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies, slowly enough to watch."""

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, *args, **kwargs):
        time.sleep(SECONDS_PER_REPLY)
        return super()._generate(*args, **kwargs)


def tool_reply(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])


def decide(claim_id: str, decision: str, payout: float) -> AIMessage:
    return tool_reply(
        "record_decision",
        {
            "claim_id": claim_id,
            "decision": decision,
            "payout": payout,
            "reason": "This is a scripted decision for the end-to-end tests.",
            "policy_section": "Section 10: How we work out your payment",
        },
    )


def script(claim_id: str) -> list[AIMessage]:
    read = tool_reply("get_claim", {"claim_id": claim_id})
    pay = tool_reply("pay_claim", {"claim_id": claim_id, "amount": 1150})
    if claim_id == "CLM-1001":
        return [
            read,
            decide(claim_id, "approve", 420),
            tool_reply("pay_claim", {"claim_id": claim_id, "amount": 420}),
            AIMessage(content="Approved and paid."),
        ]
    if claim_id == "CLM-1002":
        return [
            read,
            decide(claim_id, "approve", 1150),
            pay,
            AIMessage(content="The payment waits for a handler's sign-off."),
        ]
    return [
        read,
        decide(claim_id, "refer", 0),
        AIMessage(content="Referred to a handler."),
    ]


def stub_run(claim_id: str, thread_id: str) -> str:
    return agent.run(claim_id, thread_id, StubModel(messages=iter(script(claim_id))))


db.DB_PATH = Path(tempfile.mkdtemp()) / "e2e.db"
agent.BACKEND_URL = BACKEND_URL
worker.run = stub_run

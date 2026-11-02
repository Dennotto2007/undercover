"""The UnderCover Agent."""

import os
from collections.abc import Iterator
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, ToolCall, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
MODEL_TIMEOUT_SECONDS = 120
MAX_GRAPH_STEPS = 40
REFUSED = "Refused: "
STEP_LABELS = {
    "get_claim": "Reading the claim",
    "get_policy": "Reading the policy",
    "get_customer": "Reading the customer's claim history",
    "get_policy_wording": "Reading the policy wording",
}


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=10)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend and return its reply, or its reason for refusing."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_client_error:
        return f"{REFUSED}{response.json()['detail']}"
    response.raise_for_status()
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Read a claim: its story, items, documents, policy id and customer id."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Read a policy with its plan's limits and its add-ons."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_customer(customer_id: str) -> str:
    """Read a customer's name and claim history."""
    return call("GET", f"/api/customers/{customer_id}")


@tool
def get_policy_wording() -> str:
    """Read the policy wording."""
    return call("GET", "/api/policy-wording")


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim and return the claim's new status."""
    return call(
        "POST",
        f"/api/claims/{claim_id}/decision",
        {
            "decision": decision,
            "payout": payout,
            "reason": reason,
            "policy_section": policy_section,
        },
    )


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim the approved payout."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_customer,
    get_policy_wording,
    record_decision,
    pay_claim,
]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
        timeout=MODEL_TIMEOUT_SECONDS,
    )


def describe(tool_call: ToolCall) -> str:
    """Say in plain English what a tool call does."""
    args = tool_call["args"]
    if tool_call["name"] == "record_decision":
        payout = float(args["payout"])
        return f"Recording the decision: {args['decision']}, ${payout:,.2f}"
    if tool_call["name"] == "pay_claim":
        return f"Paying ${float(args['amount']):,.2f}"
    return STEP_LABELS.get(tool_call["name"], tool_call["name"])


def steps_in(message: AnyMessage) -> Iterator[str]:
    """Yield the lines worth showing a handler for one message."""
    if isinstance(message, ToolMessage) and message.text.startswith(REFUSED):
        yield message.text
    if isinstance(message, AIMessage):
        if message.text:
            yield message.text
        yield from map(describe, message.tool_calls)


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""
    with backend() as client:
        client.post(f"/api/claims/{claim_id}/start").raise_for_status()
        response = client.get("/api/instructions").raise_for_status()
    agent = create_agent(
        llm or model(), tools=TOOLS, system_prompt=response.json()["text"]
    )
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Claim {claim_id}"}]},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": MAX_GRAPH_STEPS,
        },
        stream_mode="updates",
    )
    reply = ""
    for update in updates:
        messages = [m for node in update.values() for m in node["messages"]]
        for message in messages:
            reply = message.text
            for text in steps_in(message):
                call(
                    "POST",
                    f"/api/claims/{claim_id}/steps",
                    {"thread_id": thread_id, "text": text},
                )
    return reply

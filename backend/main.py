"""The UnderCover backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status

from backend import claims, db, decisions, worker
from backend.claims import Record
from backend.decisions import Decision, Payment, SignOff, Step

INSTRUCTIONS = Path(__file__).parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.setup()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[Record]:
    """List the claims in the queue."""
    return claims.list_claims()


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Record:
    """Read one claim in full."""
    return claims.get_claim(claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> Record:
    """Read a policy with its plan's limits and its add-ons."""
    return claims.get_policy(policy_id)


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def get_customer(customer_id: str) -> Record:
    """Read a customer's name and claim history."""
    return claims.get_customer(customer_id)


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> dict[str, str]:
    """Read the policy wording."""
    wording = (db.DATA_DIR / "policy_wording.md").read_text(encoding="utf-8")
    return {"text": wording}


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> dict[str, str]:
    """Read the agent's instructions."""
    return {"text": INSTRUCTIONS.read_text(encoding="utf-8")}


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Record]:
    """List the claims handlers."""
    return claims.list_handlers()


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str) -> dict[str, str]:
    """Move a waiting claim to in progress."""
    return decisions.start_claim(claim_id)


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision) -> dict[str, str]:
    """Record the decision on an in progress claim and return the new status."""
    return decisions.record_decision(claim_id, decision)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: Payment) -> dict[str, str]:
    """Pay an approved claim."""
    return decisions.pay_claim(claim_id, payment.amount)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, sign_off: SignOff) -> dict[str, str]:
    """Record a handler's sign-off and make the payment."""
    return decisions.sign_off_claim(claim_id, sign_off.handler_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="record_step")
def record_step(claim_id: str, step: Step) -> dict[str, str]:
    """Record what the agent is doing on a claim."""
    return decisions.record_step(claim_id, step)


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[Record]:
    """List what the agent has done on a claim."""
    return claims.list_steps(claim_id)


@app.post(
    "/api/claims/{claim_id}/agent-run",
    operation_id="run_agent_on_claim",
    status_code=status.HTTP_202_ACCEPTED,
)
def run_agent_on_claim(claim_id: str) -> dict[str, str]:
    """Queue one waiting claim for the agent."""
    return worker.run_agent_on_claim(claim_id)


@app.post(
    "/api/queue/agent-run",
    operation_id="work_queue",
    status_code=status.HTTP_202_ACCEPTED,
)
def work_queue() -> dict[str, int]:
    """Queue every waiting claim for the agent."""
    return worker.work_queue()

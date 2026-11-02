"""The UnderCover backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend import claims, db
from backend.claims import Record


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


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Record]:
    """List the claims handlers."""
    return claims.list_handlers()

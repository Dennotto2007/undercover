"""The rules for deciding a claim and paying it."""

import sqlite3
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from fastapi import HTTPException, status
from pydantic import AfterValidator, BaseModel, Field, model_validator

from backend import db
from backend.claims import find


def to_cents(amount: float) -> float:
    """Round an amount to the cent."""
    return round(amount, 2)


class Decision(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: Annotated[float, Field(ge=0), AfterValidator(to_cents)]
    reason: str = Field(min_length=1)
    policy_section: str = Field(min_length=1)

    @model_validator(mode="after")
    def only_an_approval_pays(self) -> Self:
        if self.decision != "approve" and self.payout != 0:
            raise ValueError("Only an approval can have a payout")
        return self


class Payment(BaseModel):
    amount: Annotated[float, Field(gt=0), AfterValidator(to_cents)]


class SignOff(BaseModel):
    handler_id: str


class Step(BaseModel):
    thread_id: str
    text: str


def now() -> str:
    """Return the time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def conflict(detail: str) -> HTTPException:
    """Return the error for an action that the claim's state does not allow."""
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def require_status(
    connection: sqlite3.Connection, claim_id: str, expected: str
) -> None:
    """Refuse the action unless the claim has the expected status."""
    current = find(connection, "claims", "claim_id", claim_id)["status"]
    if current != expected:
        raise conflict(f"{claim_id} is {current}, not {expected}")


def set_status(connection: sqlite3.Connection, claim_id: str, new_status: str) -> None:
    """Move a claim to a new status."""
    connection.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ?", (new_status, claim_id)
    )


def approval_limit(connection: sqlite3.Connection) -> float:
    """Return the payout above which a handler must sign off."""
    return connection.execute("SELECT payout_approval_limit FROM company").fetchone()[0]


def status_after(decision: Decision, limit: float) -> str:
    """Return where a claim stands once this decision is recorded."""
    if decision.decision != "approve" or decision.payout == 0:
        return "decided"
    return "waiting_for_sign_off" if decision.payout > limit else "in_progress"


def start_claim(claim_id: str) -> dict[str, str]:
    """Move a waiting claim to in progress."""
    with db.transaction() as connection:
        require_status(connection, claim_id, "waiting")
        set_status(connection, claim_id, "in_progress")
    return {"status": "in_progress"}


def record_decision(claim_id: str, decision: Decision) -> dict[str, str]:
    """Record the decision on an in progress claim and return the new status."""
    with db.transaction() as connection:
        require_status(connection, claim_id, "in_progress")
        connection.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                decision.decision,
                decision.payout,
                decision.reason,
                decision.policy_section,
                now(),
            ),
        )
        new_status = status_after(decision, approval_limit(connection))
        set_status(connection, claim_id, new_status)
    return {"status": new_status}


def pay(connection: sqlite3.Connection, claim_id: str, amount: float) -> None:
    """Make a payment if the rules allow it. Every payment goes through here."""
    decision = connection.execute(
        "SELECT decision, payout FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if decision is None or decision["decision"] != "approve":
        raise conflict(f"{claim_id} has no approved decision")
    if connection.execute(
        "SELECT 1 FROM payments WHERE claim_id = ?", (claim_id,)
    ).fetchone():
        raise conflict(f"{claim_id} has already been paid")
    if amount != decision["payout"]:
        raise conflict(
            f"{amount:.2f} does not match the approved payout "
            f"of {decision['payout']:.2f}"
        )
    signed_off = connection.execute(
        "SELECT 1 FROM sign_offs WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if amount > approval_limit(connection) and signed_off is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Payment blocked: {claim_id} needs a handler's sign-off",
        )
    connection.execute(
        "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, amount, now())
    )
    set_status(connection, claim_id, "decided")


def pay_claim(claim_id: str, amount: float) -> dict[str, str]:
    """Pay an approved claim."""
    with db.transaction() as connection:
        find(connection, "claims", "claim_id", claim_id)
        pay(connection, claim_id, amount)
    return {"status": "decided"}


def sign_off_claim(claim_id: str, handler_id: str) -> dict[str, str]:
    """Record a handler's sign-off and make the payment."""
    with db.transaction() as connection:
        find(connection, "claims", "claim_id", claim_id)
        handler = find(connection, "handlers", "handler_id", handler_id)
        if not handler["can_approve_over_limit"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"{handler['name']} cannot sign off this payout",
            )
        require_status(connection, claim_id, "waiting_for_sign_off")
        connection.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)", (claim_id, handler_id, now())
        )
        payout = connection.execute(
            "SELECT payout FROM decisions WHERE claim_id = ?", (claim_id,)
        ).fetchone()[0]
        pay(connection, claim_id, payout)
    return {"status": "decided"}


def add_step(
    connection: sqlite3.Connection, claim_id: str, thread_id: str, text: str
) -> None:
    """Add a line to a claim's step log."""
    connection.execute(
        "INSERT INTO steps (claim_id, thread_id, text, created_at) VALUES (?, ?, ?, ?)",
        (claim_id, thread_id, text, now()),
    )


def record_step(claim_id: str, step: Step) -> dict[str, str]:
    """Record what the agent is doing on a claim."""
    with db.transaction() as connection:
        find(connection, "claims", "claim_id", claim_id)
        add_step(connection, claim_id, step.thread_id, step.text)
    return {"status": "recorded"}


def release(claim_id: str, thread_id: str, problem: str) -> None:
    """Put a claim the agent left in progress back in the queue."""
    with db.transaction() as connection:
        released = connection.execute(
            """
            UPDATE claims SET status = 'waiting'
            WHERE claim_id = ? AND status = 'in_progress'
            """,
            (claim_id,),
        ).rowcount
        if released:
            connection.execute("DELETE FROM decisions WHERE claim_id = ?", (claim_id,))
            add_step(connection, claim_id, thread_id, problem)

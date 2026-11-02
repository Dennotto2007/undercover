"""UnderCover's claims and the records around them."""

import json
import sqlite3
from typing import Any

from fastapi import HTTPException, status

from backend import db

Record = dict[str, Any]


def find(
    connection: sqlite3.Connection, table: str, key: str, value: str
) -> sqlite3.Row:
    """Return one row, or a 404 if it does not exist."""
    row = connection.execute(
        f"SELECT * FROM {table} WHERE {key} = ?",  # noqa: S608
        (value,),
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{value} was not found")
    return row


def list_claims() -> list[Record]:
    """Return the queue, one summary row per claim."""
    with db.reading() as connection:
        rows = connection.execute(
            """
            SELECT claims.claim_id, customers.name AS customer_name, claim_type,
                   amount_claimed, submitted_on, status, decision, payout
            FROM claims
            JOIN customers USING (customer_id)
            LEFT JOIN decisions USING (claim_id)
            ORDER BY claim_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def first_or_none(
    connection: sqlite3.Connection, query: str, claim_id: str
) -> Record | None:
    """Return the first row of a query about one claim, if there is one."""
    row = connection.execute(query, (claim_id,)).fetchone()
    return dict(row) if row else None


def get_claim(claim_id: str) -> Record:
    """Return one claim in full, with its decision, sign-off and payment."""
    with db.reading() as connection:
        claim = find(connection, "claims", "claim_id", claim_id)
        customer = find(connection, "customers", "customer_id", claim["customer_id"])
        decision = first_or_none(
            connection,
            """
            SELECT decision, payout, reason, policy_section, decided_at
            FROM decisions WHERE claim_id = ?
            """,
            claim_id,
        )
        sign_off = first_or_none(
            connection,
            """
            SELECT handler_id, name AS handler_name, signed_off_at
            FROM sign_offs JOIN handlers USING (handler_id) WHERE claim_id = ?
            """,
            claim_id,
        )
        payment = first_or_none(
            connection,
            "SELECT amount, paid_at FROM payments WHERE claim_id = ?",
            claim_id,
        )
    return dict(claim) | {
        "customer_name": customer["name"],
        "items": json.loads(claim["items"]),
        "documents": json.loads(claim["documents"]),
        "decision": decision,
        "sign_off": sign_off,
        "payment": payment,
    }


def get_policy(policy_id: str) -> Record:
    """Return a policy with its plan's limits and its add-ons."""
    with db.reading() as connection:
        policy = json.loads(
            find(connection, "policies", "policy_id", policy_id)["record"]
        )
        plan = find(connection, "plans", "plan", policy["plan"])
        add_ons = [
            find(connection, "add_ons", "add_on", add_on)
            for add_on in policy["add_ons"]
        ]
    return policy | {
        "plan_details": json.loads(plan["record"]),
        "add_on_details": [json.loads(add_on["record"]) for add_on in add_ons],
    }


def get_customer(customer_id: str) -> Record:
    """Return a customer's name and claim history, without contact details."""
    with db.reading() as connection:
        customer = find(connection, "customers", "customer_id", customer_id)
    return dict(customer) | {"previous_claims": json.loads(customer["previous_claims"])}


def list_handlers() -> list[Record]:
    """Return the claims handlers."""
    with db.reading() as connection:
        rows = connection.execute(
            "SELECT * FROM handlers ORDER BY handler_id"
        ).fetchall()
    return [
        dict(row) | {"can_approve_over_limit": bool(row["can_approve_over_limit"])}
        for row in rows
    ]

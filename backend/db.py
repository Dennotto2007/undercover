"""UnderCover's SQLite database and its seed data."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "undercover.db"
DATA_DIR = ROOT / "data"
SEED_FILES = (
    "claims.json",
    "company.json",
    "customers.json",
    "handlers.json",
    "plans.json",
    "policies.json",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS company (
    name TEXT PRIMARY KEY,
    payout_approval_limit REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (plan TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS add_ons (add_on TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    customer_since TEXT NOT NULL,
    previous_claims TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS handlers (
    handler_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    can_approve_over_limit INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies,
    customer_id TEXT NOT NULL REFERENCES customers,
    claim_type TEXT NOT NULL,
    submitted_on TEXT NOT NULL,
    incident_date TEXT NOT NULL,
    incident_location TEXT NOT NULL,
    summary TEXT NOT NULL,
    story TEXT NOT NULL,
    items TEXT NOT NULL,
    amount_claimed REAL NOT NULL,
    documents TEXT NOT NULL,
    status TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    """Open a connection that returns rows by column name."""
    connection = sqlite3.connect(DB_PATH, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def reading() -> Iterator[sqlite3.Connection]:
    """Open a connection for reads."""
    with closing(connect()) as connection:
        yield connection


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Open a write transaction, which commits at the end or rolls back on an error."""
    with closing(connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        yield connection


def load(name: str) -> Any:
    """Read one seed file."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed(connection: sqlite3.Connection) -> None:
    """Load the business records into empty tables."""
    company = load("company.json")
    plans = load("plans.json")
    connection.execute(
        "INSERT INTO company VALUES (?, ?)",
        (company["name"], company["payout_approval_limit"]),
    )
    connection.executemany(
        "INSERT INTO plans VALUES (?, ?)",
        [(plan["plan"], json.dumps(plan)) for plan in plans["plans"]],
    )
    connection.executemany(
        "INSERT INTO add_ons VALUES (?, ?)",
        [(add_on["add_on"], json.dumps(add_on)) for add_on in plans["add_ons"]],
    )
    connection.executemany(
        "INSERT INTO policies VALUES (?, ?)",
        [(p["policy_id"], json.dumps(p)) for p in load("policies.json")],
    )
    connection.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?)",
        [
            (
                c["customer_id"],
                c["name"],
                c["customer_since"],
                json.dumps(c["previous_claims"]),
            )
            for c in load("customers.json")
        ],
    )
    connection.executemany(
        "INSERT INTO handlers VALUES (?, ?, ?, ?)",
        [
            (h["handler_id"], h["name"], h["role"], h["can_approve_over_limit"])
            for h in load("handlers.json")
        ],
    )
    connection.executemany(
        """
        INSERT INTO claims VALUES (
            :claim_id, :policy_id, :customer_id, :claim_type, :submitted_on,
            :incident_date, :incident_location, :summary, :story, :items,
            :amount_claimed, :documents, 'waiting'
        )
        """,
        [
            c
            | {"items": json.dumps(c["items"]), "documents": json.dumps(c["documents"])}
            for c in load("claims.json")
        ],
    )


def setup() -> None:
    """Create the tables and seed them the first time the backend starts."""
    with reading() as connection:
        connection.executescript(SCHEMA)
    with transaction() as connection:
        if connection.execute("SELECT 1 FROM claims LIMIT 1").fetchone() is None:
            seed(connection)

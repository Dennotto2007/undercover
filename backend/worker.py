"""Runs the agent on claims, one at a time, in the order they were queued."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from agent.main import run
from backend import claims, decisions

executor = ThreadPoolExecutor(max_workers=1)


def work_on(claim_id: str) -> None:
    """Run the agent on a claim, and put the claim back if it did not finish."""
    thread_id = str(uuid4())
    try:
        run(claim_id, thread_id)
        problem = "the run ended before the claim was finished"
    except Exception as error:
        problem = str(error) or type(error).__name__
    decisions.release(
        claim_id, thread_id, f"The agent stopped before finishing: {problem}"
    )


def run_agent_on_claim(claim_id: str) -> dict[str, str]:
    """Queue one waiting claim for the agent."""
    if claims.get_claim(claim_id)["status"] != "waiting":
        raise decisions.conflict(f"{claim_id} is not waiting")
    executor.submit(work_on, claim_id)
    return {"status": "queued"}


def work_queue() -> dict[str, int]:
    """Queue every waiting claim for the agent."""
    waiting = claims.waiting_claims()
    for claim_id in waiting:
        executor.submit(work_on, claim_id)
    return {"started": len(waiting)}

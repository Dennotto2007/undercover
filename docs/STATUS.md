# Status

The pilot is being built from `docs/PLAN.md`.

- `backend/`: SQLite records seeded from `data/`, with the read operations for claims, policies, customers, the policy wording and handlers, and the write operations to start a claim, record a decision, pay and sign off. A payout over the limit cannot be paid without a handler's sign-off. A background worker runs the agent on queued claims, one at a time
- `agent/`: the UnderCover Agent, with the entry point `run(claim_id, thread_id)`. It reads a claim, its policy, the customer's history and the policy wording through the API, records a decision, pays when the rules allow and logs each step. Its instructions are in `backend/instructions.md`
- `dashboard/`: the claims queue, each claim in full with its decision, and the agent's instructions, read only, in light and dark modes
- `e2e/`: Playwright tests of those pages. They start the real app and agent with a stub model and a temporary database, on ports 8001 and 5174, so they can run while `npm run dev` is running

## Running it

`npm run dev` starts the backend on port 8000 and the dashboard on port 5173. The backend creates and seeds `undercover.db` the first time it starts.

# Status

The pilot is being built from `docs/PLAN.md`.

- `backend/`: SQLite records seeded from `data/`, with the read operations for claims, policies, customers, the policy wording and handlers, and the write operations to start a claim, record a decision, pay and sign off. A payout over the limit cannot be paid without a handler's sign-off. A background worker runs the agent on queued claims, one at a time
- `agent/`: the UnderCover Agent, with the entry point `run(claim_id, thread_id)`. It reads a claim, its policy, the customer's history and the policy wording through the API, records a decision, pays when the rules allow and logs each step. Its instructions are in `backend/instructions.md`
- `dashboard/`: still the skeleton, with one page that shows whether the backend is up
- `e2e/`: one test of that page

## Running it

`npm run dev` starts the backend on port 8000 and the dashboard on port 5173. The backend creates and seeds `undercover.db` the first time it starts.

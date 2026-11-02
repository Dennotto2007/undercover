# Status

The claims pilot is built, as planned in `docs/PLAN.md`.

- `backend/`: SQLite records seeded from `data/`, and the API for claims, policies, customers, the policy wording, the agent's instructions, decisions, payments, sign-offs and the agent's steps. A payout over the limit cannot be paid without a handler's sign-off. A background worker runs the agent on queued claims, one at a time
- `agent/`: the UnderCover Agent, with the entry point `run(claim_id, thread_id)`. It reads a claim, its policy, the customer's history and the policy wording through the API, records a decision, pays when the rules allow and logs each step. Its instructions are in `backend/instructions.md`
- `dashboard/`: an overview with claim counts, total payouts and claim types by status, the claims queue, each claim in full with its decision, the agent's steps as it works, and the agent's instructions, read only, in light and dark modes. Handlers can run the agent on a claim, work the whole queue and sign off a payout over the limit
- `e2e/`: Playwright tests of those pages and of the agent's journeys, with a stub model

## Running it

`npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173, which opens on the overview. The backend creates and seeds `undercover.db` the first time it starts.

Run agent and Work the queue use the real model, so they spend API credit. Work the queue runs every waiting claim, up to 25.

`npm run check` runs every check. Its Playwright tests use a stub model and a temporary database on ports 8001 and 5174, so they can run while `npm run dev` is running.

## Resetting the data

Stop the backend, delete `undercover.db` and start the backend again.

## Known limits

- In the first full queue run, 3 of the 25 claims stopped after reading their records, without a decision. They went back to `Waiting` with nothing paid, and each can be run again. The cause is not known yet.
- Accuracy against the handlers' decisions has not been measured. `data/evals/` stays closed until the evaluations are built.
- The agent works from the policy wording alone, so it will miss claims that need the claims manual.
- There is no sign-in, so the API cannot tell a handler from any other caller. Anyone at the screen can sign off under any handler's name. The agent cannot, because it has no tool for it.
- A referred claim ends as `Decided`, with `Referred` in the queue. There is no screen yet for a handler to finish it.

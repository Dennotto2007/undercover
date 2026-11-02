# Status

The pilot is being built from `docs/PLAN.md`.

- `backend/`: SQLite records seeded from `data/`, with the read operations for claims, policies, customers, the policy wording and handlers
- `agent/`: still the skeleton, with one tool that calls the health route
- `dashboard/`: still the skeleton, with one page that shows whether the backend is up
- `e2e/`: one test of that page

## Running it

`npm run dev` starts the backend on port 8000 and the dashboard on port 5173. The backend creates and seeds `undercover.db` the first time it starts.

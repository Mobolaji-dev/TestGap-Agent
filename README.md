# TestGap Finder

TestGap Finder is an agent for finding high-priority Python test gaps and producing tests whose value can be checked with mutation testing.

## Current implementation slice

The API currently supports configured project discovery, asynchronous run creation, run status, cancellation, and SSE events. The LangGraph workflow inspects the selected repository, runs a baseline pytest/coverage pass, and ranks uncovered files with a transparent heuristic. neatlogs initializes at app startup when available. Test generation, repair, and mutation verification are planned workflow stages and are not implemented yet.

The backend uses the layering from `hammet-core` (routes → services → repositories) and the agent layout from `langgraph-wa-agent` (`state`, `nodes`, `prompts`, `graph`).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set TESTGAP_REPOSITORY_PATH and NEATLOGS_API_KEY in .env.
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the API schema. The frontend dev server at `http://localhost:5173` is allowed by the default CORS configuration.

## Frontend API

- `GET /api/v1/projects`
- `POST /api/v1/runs` with `{ "project_id": "...", "target_limit": 3, "repair_limit": 2, "verify_mutations": true }`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/events` (SSE; accepts `?after=<event_id>`)
- `POST /api/v1/runs/{run_id}/cancel`

Run/event schemas are defined in `schemas/run.py`; project schemas are in `schemas/project.py`.

## Current boundaries

- Only a server-configured repository path can be selected; the browser cannot submit an arbitrary filesystem path.
- Baseline commands run with `shell=False`, bounded runtime, and bounded captured output.
- This initial run repository is process-local and resets when the API restarts.
- Baseline commands run from a temporary copy of the configured project; the inspected checkout is not modified by this step.
- When `NEATLOGS_API_KEY` is set, each LangGraph run is sent to the `testgap-agent` Neatlogs workflow through the supported LangChain callback. Leave it blank for local-only runs.
- Entire is used during development to capture repository context and checkpoints; it is not a runtime dependency. cfo.ai is used to prepare the required pricing, cost, revenue, and runway model; it is not part of the request path.

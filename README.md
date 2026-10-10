# TestGap Finder

TestGap Finder is an agent for finding high-priority Python test gaps and producing tests whose value can be checked with mutation testing.

## Current implementation slice

The API supports configured project discovery, asynchronous run creation, run status, cancellation, and SSE events. The LangGraph workflow inspects the selected repository, runs a baseline pytest/coverage pass, ranks uncovered files, and drafts tests for the highest-ranked gap with the configured LiteLLM model. Candidate tests are returned for review but are not written into the selected repository or executed yet; repair and mutation verification remain planned.

The backend uses the layering from `hammet-core` (routes → services → repositories) and the agent layout from `langgraph-wa-agent` (`state`, `nodes`, `prompts`, `graph`).
Run records, baseline coverage details, ranked targets, and events are stored in SQLite at `.runs/testgap.sqlite3` by default; set `TESTGAP_RUN_DATABASE_PATH` to choose another location.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set TESTGAP_REPOSITORY_PATH and LITELLM_API_KEY in .env.
# NEATLOGS_API_KEY is separate and enables trace export.
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
- Run results and events survive API restarts in the SQLite run repository.
- Baseline commands run from a temporary copy of the configured project; the inspected checkout is not modified by this step.
- Set `LITELLM_API_KEY` in the ignored local `.env`. The LiteLLM base URL defaults to `https://litellm.vision.aivar.app/v1`; `LITELLM_MODEL` defaults to `claude-haiku` and can be set to any model ID shown in the hackathon portal. One run drafts tests for at most the top-ranked target.
- Set a separate `NEATLOGS_API_KEY` to export runtime traces. Without it, model calls still work but neatlogs export is disabled. Source excerpts and repository documentation are sent to the selected model; only use repositories you are authorized to share.
- Entire is used during development to capture repository context and checkpoints; it is not a runtime dependency. cfo.ai is used to prepare the required pricing, cost, revenue, and runway model; it is not part of the request path.

## Hackathon partner setup

- **neatlogs:** Set `NEATLOGS_API_KEY` in the ignored local `.env`. Run the app and inspect the `testgap-agent` workflow in the Neatlogs dashboard. The current graph callback records the LangGraph run; a real run is still needed to capture demo evidence.
- **Entire:** Install the Entire CLI, then run `entire enable --agent codex --skip-push-sessions`, `entire plugin install graph`, and `entire graph init-agents --repo .`. The last command adds `AGENTS.md`/`CLAUDE.md` instructions. Approve the installed hooks in Codex with `/hooks` before expecting automatic session checkpoints. The Graph setup and query are recorded in [evidence/entire-graph.md](evidence/entire-graph.md).
- **cfo.ai:** Use the prompt in [evidence/cfo-ai-model-brief.md](evidence/cfo-ai-model-brief.md) to create an 18-month, three-scenario business model. Save a cfo.ai export or screenshot in `evidence/` after the account is connected; the brief is prepared input, not proof of a completed cfo.ai model.
- **AWS / Bedrock (optional):** Use a local AWS profile after the event reissues the exposed credentials. Keep credentials outside this repository. The Bedrock test-writer adapter has not been implemented yet.

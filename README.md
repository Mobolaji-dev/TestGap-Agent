# TestGap Finder

TestGap Finder is an agent for finding high-priority Python test gaps and producing tests whose value can be checked with mutation testing.

## Current implementation slice

The API supports configured project discovery, asynchronous run creation, run status, cancellation, and SSE events. A run can use either a server-configured local project or a public GitHub HTTPS URL. The LangGraph workflow inspects the selected repository, measures baseline pytest/coverage, ranks uncovered files, drafts a test for the highest-ranked gap with the configured LiteLLM model, and validates the candidate with the repository's suite in a disposable copy. Only passing candidates are offered as test-only patches; the source checkout is never edited. Repair and mutation verification remain planned.

The backend uses the layering from `hammet-core` (routes → services → repositories) and the agent layout from `langgraph-wa-agent` (`state`, `nodes`, `prompts`, `graph`).
Run records, baseline coverage details, ranked targets, and events are stored in SQLite at `.runs/testgap.sqlite3` by default; set `TESTGAP_RUN_DATABASE_PATH` to choose another location.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optionally set TESTGAP_REPOSITORY_PATH and set LITELLM_API_KEY in .env.
# NEATLOGS_API_KEY is separate and enables trace export.
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the API schema. The frontend dev server at `http://localhost:5173` is allowed by the default CORS configuration.

## Frontend API

- `GET /api/projects`
- `POST /api/runs` with either `{ "project_id": "..." }` or `{ "repository_url": "https://github.com/owner/repository" }`, plus optional run settings.
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events` (SSE; accepts `?after=<event_id>`)
- `POST /api/runs/{run_id}/cancel`
- `GET /api/runs/{run_id}/diff` (JSON response containing the generated test-only unified diff)
- `GET /api/runs/{run_id}/patch` (downloads the same diff as a `.patch` file)

Run/event schemas are defined in `schemas/run.py`; project schemas are in `schemas/project.py`.

## Current boundaries

- Remote scans accept public GitHub HTTPS URLs only. Private repositories, other Git hosts, URL credentials, query strings, and fragments are rejected.
- GitHub repository metadata is checked before cloning. The default clone timeout is 120 seconds and the default repository-size limit is 200 MB; configure these with `TESTGAP_REPOSITORY_CLONE_TIMEOUT_SECONDS` and `TESTGAP_REPOSITORY_MAX_SIZE_MB`.
- Remote clones use shallow, blob-filtered Git and are removed after the run. The generated test-only patch is saved with the run so it remains downloadable after cleanup.
- Scanning and candidate verification execute Python code from the submitted repository. Candidate tests run in a disposable copy with a reduced environment, but this MVP does not provide an OS/container sandbox. Only scan repositories you trust.
- The browser cannot submit an arbitrary filesystem path.
- Baseline commands run with `shell=False`, bounded runtime, and bounded captured output.
- Run results and events survive API restarts in the SQLite run repository.
- Baseline commands run from a temporary copy of the configured project; the inspected checkout is not modified by this step.
- Set `LITELLM_API_KEY` in the ignored local `.env`. The LiteLLM base URL defaults to `https://litellm.vision.aivar.app/v1`; `LITELLM_MODEL` defaults to `claude-haiku` and can be set to any model ID shown in the hackathon portal. One run drafts tests for at most the top-ranked target.
- Set a separate `NEATLOGS_API_KEY` to export runtime traces. Without it, model calls still work but neatlogs export is disabled. Source excerpts and repository documentation are sent to the selected model; only use repositories you are authorized to share.
- neatlogs is the runtime tracing integration. Entire is the development-time repository context/checkpoint integration, not a runtime dependency. cfo.ai is the separate business-planning tool required for the submission; it does not belong in the API request path.

## Hackathon partner setup

- **neatlogs:** Set `NEATLOGS_API_KEY` in the ignored local `.env`. The backend initializes the SDK, attaches its LangGraph callback to graph execution, and wraps the LiteLLM OpenAI-compatible client. Capture a real run from the `testgap-analysis` workflow in the Neatlogs dashboard for submission evidence; code wiring alone does not prove successful trace export.
- **Entire:** Install the Entire CLI, then run `entire enable --agent codex --skip-push-sessions`, `entire plugin install graph`, and `entire graph init-agents --repo .`. The last command adds `AGENTS.md`/`CLAUDE.md` instructions. Approve the installed hooks in Codex with `/hooks` before expecting automatic session checkpoints. The Graph setup and query are recorded in [evidence/entire-graph.md](evidence/entire-graph.md).
- **cfo.ai:** Use the prompt in [evidence/cfo-ai-model-brief.md](evidence/cfo-ai-model-brief.md) to create an 18-month, three-scenario business model. Save a cfo.ai export or screenshot in `evidence/`; this is still pending and the brief is not proof of a completed cfo.ai model.
- Current proof gaps and submission evidence checklist: [evidence/hackathon-technology-status.md](evidence/hackathon-technology-status.md).
- **AWS / Bedrock (optional):** Use a local AWS profile after the event reissues the exposed credentials. Keep credentials outside this repository. The Bedrock test-writer adapter has not been implemented yet.

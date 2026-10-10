# TestGap Finder — Frontend Technical Specification

**Audience:** React frontend developer  
**API status:** Backend code exposes `/api` routes  
**Production frontend URL:** Pending frontend deployment  
**Production API URL:** https://testgap-agent.onrender.com/

This document describes the frontend integration contract for the current TestGap Finder backend. The backend currently supports project listing, scan creation and status/events, cancellation, and generated-test diff/patch retrieval. It does not yet execute generated tests, repair them, or run mutation verification; render those results as unavailable until those backend capabilities are implemented.

## 1. Product flow

1. Load available local/demo projects or enter a public GitHub repository URL.
2. Configure target count, repair limit, and mutation verification preference.
3. Create a run and show its `run_id` and current status.
4. Stream run events over Server-Sent Events (SSE), while fetching the run resource for canonical state.
5. Show baseline results, ranked targets, warnings, and any generated test draft.
6. When a draft exists, preview its unified diff and let the user download the patch.

## 2. API Communication & Standard Headers

### Base URL

Configure the origin once; append API paths without duplicating `/api`:

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_PREFIX = "/api";
```

Production API value: `https://testgap-agent.onrender.com/`. The root path `/` is not an API route; `/docs` is FastAPI's interactive API documentation. The API origin must not end with `/api`; endpoint paths below include the `/api` prefix. Verify `/health` and `/api/projects` for health and configured local projects.

### Headers

For JSON requests, send:

```http
Accept: application/json
Content-Type: application/json
```

For the SSE endpoint, use `Accept: text/event-stream`. The current API has no user authentication header. Do not send model or Neatlogs credentials from the browser; those belong in the backend environment.

The backend currently allows localhost Vite origins by default. When hosting the frontend separately, configure `TESTGAP_CORS_ORIGINS` on the backend with the exact frontend origin(s), such as `https://your-frontend.example`.

### Build and local development

Frontend:

```bash
npm install
npm run dev
npm run build
```

Backend local start:

```bash
sh -c 'uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"'
```

Bind to `0.0.0.0` and use the platform-provided `PORT`; `8000` is the local fallback. Make the deployment's published application port match the listener. Set `VITE_API_BASE_URL=http://localhost:8000` in the frontend environment for local development.

## 3. Primary UI Modules & Views

### Project selector / start view

- Fetch projects from `GET /api/projects`.
- Allow selecting a configured local project or entering a public GitHub HTTPS repository URL.
- Show project name, language, detected test framework, readiness, and warning for configured local projects.
- Disable run creation when the project is not ready; explain that pytest is required.
- For a GitHub URL, submit it in `repository_url` when starting a run. Show the clone step and any public/private, size-limit, or timeout errors from the run events.
- Provide controls for `target_limit` (1–10), `repair_limit` (0–2), and `verify_mutations`.
- Start with a demo project selected only if the API returns it; do not invent a project ID.

### Run progress view

- Show run status, current step, elapsed time, and event timeline.
- Connect to the run's SSE endpoint and deduplicate events by `event_id`.
- Show cancel while the run is `queued` or `running`.
- Re-fetch run state after reconnect and on terminal events.

### Results view

- Show baseline coverage when present, ranked targets, test candidate drafts, and warnings.
- For metrics that are `null`, not populated, or not yet supported, render “Not available” rather than `0%`.
- The current backend may return a generated test candidate when the model is configured. Treat it as a draft.
- Show a “Preview diff” and “Download patch” action when a candidate exists. These actions do not apply files to the source project.
- Mutation score and after-coverage are not currently computed; do not present placeholder values as results.

### Empty, loading, warning, and failure states

- Empty: no configured projects; explain that the backend needs a local/demo repository.
- Loading: project list or run state is being fetched.
- Warning: show each run warning in context, including model/provider or trace configuration issues.
- Failed: show the API error and offer a retry where retry is safe.
- Completed with warnings: show available baseline/ranking output and preserve warnings.

## 4. Complete API Endpoint Reference

All endpoints use the `/api` prefix. JSON fields use `snake_case`.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `GET` | `/api/projects` | List configured local/demo projects | `200` JSON |
| `POST` | `/api/runs` | Start a scan of a configured project or public GitHub repository | `202` `RunResponse` |
| `GET` | `/api/runs/{run_id}` | Fetch canonical run state and results | `200` `RunResponse` |
| `GET` | `/api/runs/{run_id}/events?after={event_id}` | Stream events over SSE; `after` resumes after an event ID | `200` `text/event-stream` |
| `POST` | `/api/runs/{run_id}/cancel` | Request cancellation | `200` `RunResponse` |
| `GET` | `/api/runs/{run_id}/diff` | Return generated test-only unified diff | `200` `{ run_id, diff }` |
| `GET` | `/api/runs/{run_id}/patch` | Download generated test-only patch | `200` `text/x-diff` attachment |
| `GET` | `/health` | Liveness check | `200` `{ "status": "ok" }` |

### Create run

Request:

```json
{
  "repository_url": "https://github.com/owner/repository",
  "target_limit": 3,
  "repair_limit": 2,
  "verify_mutations": true
}
```

Provide exactly one of `project_id` or `repository_url`. GitHub URLs must use HTTPS and point to a public repository. The default clone limit is 200 MB and clone timeout is 120 seconds. `target_limit` is 1–10. `repair_limit` is 0–2. Both fields are optional; backend defaults are 3 and 2. `verify_mutations` defaults to `true`.

The `202` response is a `RunResponse`, not a small `{run_id, events_url}` envelope. Construct the events URL from the returned `run_id`:

```text
GET /api/runs/{run_id}/events
```

### Project response

```ts
type ProjectResponse = {
  id: string;
  name: string;
  language: string;
  test_framework: string | null;
  path_label: string;
  ready: boolean;
  warning: string | null;
};

type ProjectListResponse = { projects: ProjectResponse[] };
```

### Run response

```ts
type RunStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled";

type RiskTarget = {
  path: string;
  symbol: string;
  line_start: number;
  line_end: number;
  uncovered_lines: number[];
  priority_score: number;
  rationale: string[];
};

type TestCandidate = {
  target_path: string;
  test_path: string;
  content: string;
  model: string;
};

type RunMetrics = {
  coverage_before_pct: number | null;
  coverage_after_pct: number | null;
  mutations_killed: number;
  mutations_attempted: number;
  tests_added: number;
  duration_ms: number;
};

type RunEvent = {
  event_id: number;
  run_id: string;
  timestamp: string;
  type: string;
  step: string;
  status: string;
  message: string;
  data: Record<string, unknown>;
};

type RunResponse = {
  run_id: string;
  project_id: string;
  repository_url: string | null;
  repository_url: string | null;
  status: RunStatus;
  current_step: string | null;
  created_at: string;
  updated_at: string;
  events: RunEvent[];
  targets: RiskTarget[];
  baseline: Record<string, unknown>;
  candidate_tests: TestCandidate[];
  metrics: RunMetrics;
  trace_url: string | null;
  warnings: string[];
};
```

### Diff and patch responses

`GET /api/runs/{run_id}/diff` returns:

```json
{ "run_id": "run_abc123", "diff": "--- /dev/null\n+++ b/tests/test_example_testgap.py\n..." }
```

`GET /api/runs/{run_id}/patch` returns the same unified diff as a downloadable `.patch` file. Both endpoints return `409` when no generated candidate is available. The diff is a preview/export artifact; it does not mean tests have been run or applied.

### SSE event envelope

Each `data:` payload is a JSON `RunEvent`. The stream also sets SSE `id` to `event_id` and SSE `event` to the event `type`.

```json
{
  "event_id": 2,
  "run_id": "run_abc123",
  "timestamp": "2026-10-10T12:43:00Z",
  "type": "step.completed",
  "step": "baseline",
  "status": "success",
  "message": "Baseline scan completed.",
  "data": {}
}
```

Listen for event types as strings and render unknown types generically so new backend event types do not break the timeline. Current graph steps may emit `step.completed`, `warning`, and terminal `run.*` events.

## 5. React Integration Patterns & Recommendations

### Typed API helper

Create a single API module that joins the configured origin and endpoint path, sets JSON headers, parses JSON errors, and throws a typed error containing `status` and `detail`. Keep the API origin in a Vite environment variable; never hard-code a developer machine's IP in source.

### Run lifecycle

1. Call `POST /api/runs`; store the returned `run_id`.
2. Fetch `GET /api/runs/{run_id}` to hydrate the page.
3. Open `EventSource` at `/api/runs/{run_id}/events` and append each parsed event by `event_id`.
4. On reconnect, pass the last event ID using `?after=...`; the endpoint emits keep-alives while active.
5. Re-fetch the run after terminal events (`run.completed`, `run.failed`, `run.cancelled`) and close the `EventSource`.
6. On cancel, POST to `/cancel`, then refresh run state.

### State management

- Keep server state (`projects`, `run`, `events`) separate from transient UI state (selected project, form fields, expanded rows).
- Use request cancellation/cleanup in React effects to avoid stale responses when switching runs.
- Reuse one event parser and dedupe repeated events by ID.
- Keep errors local to the affected panel; preserve useful run data if the SSE connection drops.

### Network and resilience

- Use `AbortController` for regular fetch calls and clear timers/listeners on unmount.
- SSE is one-way; use normal `fetch` for create, cancel, status, diff, and patch.
- If SSE cannot connect, fall back to polling `GET /api/runs/{run_id}` at a modest interval and disclose that live updates are unavailable.
- Do not retry `POST /api/runs` automatically after a network timeout; the original request may have created a run. Offer a deliberate retry action.

## 6. UI Rendering Guidance for Components

- **Status badge:** map the six `RunStatus` strings to distinct labels/colors; always include text, not color alone.
- **Coverage card:** show a percentage only when a number exists; show an em dash/“Not available” for null.
- **Risk target row:** show `path`, `symbol`, line range, `priority_score`, and each rationale. Label score as heuristic priority, not bug probability.
- **Event timeline:** show timestamp, step, status, message; allow `data` details to expand without assuming a fixed shape.
- **Candidate test panel:** display `test_path`, `target_path`, model name, and draft content; identify it as generated/unverified.
- **Diff preview:** render unified diff as text with safe escaping; never inject raw HTML. Keep download available via the patch endpoint.
- **Warnings panel:** make warnings visible and non-blocking where the run still has usable output.
- **Cancel control:** show only for queued/running; disable while the cancel request is in flight.
- **Accessibility:** keyboard-accessible controls, visible focus, semantic headings, and `aria-live="polite"` for new progress events.

## 7. Standard Error Response Format

FastAPI errors use a JSON `detail` property.

Typical application error:

```json
{ "detail": "Run not found" }
```

Validation errors may return an array under `detail`:

```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "target_limit"],
      "msg": "Input should be less than or equal to 10",
      "input": 12,
      "ctx": { "le": 10 }
    }
  ]
}
```

Handle at minimum: `404` unknown project/run, `409` diff/patch unavailable, `422` invalid request body, and `5xx` server failures. Convert either string or array `detail` into a readable message; retain raw response details in development logs only.

## 8. Current implementation boundaries

- The code exposes `/api` (not `/api/v1`).
- The run graph currently performs baseline scanning and target ranking, and may draft a test for one target when the model is configured.
- The generated test is not automatically written into the repository, executed, repaired, or mutation-verified yet.
- `coverage_after_pct`, mutation counts, and `tests_added` are response fields but are not evidence that those capabilities ran. Render actual unset/default values honestly.
- Production API URL is `https://test-gap-agent.vercel.app/`.
- Production frontend URL remains **Pending frontend deployment**.

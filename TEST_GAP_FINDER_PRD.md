# TestGap Finder — product and technical brief

**Version:** 0.1 · **Prepared:** 9 October 2026 · **Hackathon:** neatHack 2026  
**Audience:** product/engineering, especially the frontend developer  
**Status:** pre-build plan; write application code only during the hackathon window.

## 1. Product in one sentence

TestGap Finder is a Python repository agent that identifies a small set of high-risk, under-tested code, proposes focused pytest tests, repairs those tests when they fail, and checks whether each accepted test detects a controlled code mutation.

**Demo promise:** choose a prepared Python repository, start one run, and watch the agent deliver a tested patch with measurable baseline-to-after coverage and mutation evidence.

## 2. Why this fits neatHack

neatHack asks for an agent that completes a substantial task end to end, with planning, tool use, state, context, execution, recovery, verification, and iteration. Every project must use neatlogs, Entire, and cfo.ai, and the demo must show all three. The published judging weights are: agent 30%, partner tools 25%, demo 20%, building in public 15%, usefulness/originality 10%. Claims need checkable evidence, including before/after runs, a visible recovery, partner evidence, a public repo with hackathon-period commits, and a demo video of at most three minutes. [Hackathon challenge, requirements, judging and submission details](https://neatlogs.com/hackathon#challenge)

This concept has a clear, observable agent loop: inspect → rank → plan → generate → run → diagnose/revise → mutate → verify → report. The product should make that loop visible rather than present a generic chat interface.

## 3. Problem and target user

### Problem

Developers inherit Python code with uneven tests. Coverage percentages show where lines are missed, but do not tell a developer which gap is risky, what test to add, or whether the new test would catch a realistic regression. Manually doing that investigation takes time, and generated tests can pass while asserting very little.

### Primary user

An individual developer or small team maintaining a Python repository who wants a reviewable first pass at meaningful regression tests.

### Job to be done

“When I point to a Python repo, help me find a risky untested behavior, add useful tests, and show me evidence those tests would fail if the behavior regressed.”

### Initial scope

- Python repositories using pytest.
- Local, preselected demo repository; no GitHub app or remote repository writes in the MVP.
- One target module or a handful of ranked functions per run.
- Agent proposes test-file changes only. The original source tree remains untouched during mutant trials.
- Human reviews and applies/exports the final test patch.

## 4. Product requirements

### Core workflow

1. **Select project.** Show repository name/path, detected Python/pytest status, and a clear “Start analysis” action. For the hackathon demo, offer a seeded sample repo so setup cannot derail the presentation.
2. **Baseline.** Run the existing test suite and coverage report. Show command, pass/fail, duration, line coverage, and files with uncovered executable lines.
3. **Rank gaps.** Produce a short ranked list with file/function, uncovered lines, risk score, and a plain-language reason. Risk combines uncovered executable lines, public entry points, branching/exception behavior, and dependency on user input. Show that this is a heuristic, not a claim of production incident probability.
4. **Plan.** Display the selected targets and planned actions before execution starts. The agent should select a small number of targets to keep runtime and output bounded.
5. **Generate tests.** Write candidate tests into an isolated working copy/branch. Preserve repository conventions and existing test layout.
6. **Run and recover.** Run the candidate tests. On failure, capture the relevant traceback, let the agent revise the candidate, and retry at most twice. Keep each attempt visible. If the baseline suite fails, stop the generation loop and report that the baseline is unhealthy.
7. **Mutation verification.** For each accepted test, apply a controlled mutation to a disposable copy of the target source and run the relevant test. A “killed” mutant means the test failed against the mutation and passed against the original. A surviving mutant is explicitly marked as weak/unverified; do not count it as verified.
8. **Report.** Show baseline and resulting line coverage, tests added, mutation results, run duration, and links/IDs for the neatlogs run(s). Provide a reviewable diff and allow download/copy of the test patch.

### Acceptance criteria

- A user can complete the seeded happy-path run without configuring a model or editing environment variables in the UI.
- Baseline and final coverage are computed by coverage.py, and all displayed values can be traced to saved run results.
- The agent never reports a test as verified unless it passes on the original source and fails on the corresponding mutated source.
- Failed command output, agent decision, retry count, and final disposition are visible in the run timeline.
- Test changes are isolated from the original source tree and shown as a diff before export.
- The run can finish as `completed`, `completed_with_warnings`, `failed`, or `cancelled`; failure states include a next step.
- The UI remains useful when instrumentation or external model services are unavailable: show the local result and an observability warning rather than inventing a trace link.

## 5. What is intentionally out of scope

- Supporting arbitrary languages or non-pytest test runners.
- Applying generated source-code fixes, committing, pushing, or opening PRs automatically.
- Running arbitrary repository commands outside the allowlisted test/coverage/mutation commands.
- Multi-agent orchestration, long-running background monitoring, full mutation testing of every line, or a general-purpose coding assistant.
- Promising that increased coverage means correctness. Mutation results are evidence about selected mutants only.

## 6. Partner technology plan

The event requires a real role for all three required partners. Keep these roles explicit in the UI, repository evidence, and demo.

| Technology | Concrete role in this product | Evidence to capture |
|---|---|---|
| **neatlogs** | Instrument each analysis as a trace with spans for baseline, repository inspection, target ranking, plan, each model call, each tool call, test attempt/retry, mutation trial, and report. Attach run ID/URL to the result view. Compare a first run with an improved run. | Two linked traces; span tree showing tool inputs/results, retry/failure, elapsed time and, where available, tokens/cost. Redact source snippets/secrets. |
| **Entire** | Use the coding-agent workflow and repository context tooling during development; use `entire-graph` to understand the app repo and preserve code-change/session context with checkpoints. Keep checkpoints around significant implementation changes. | `entire` checkpoint/session evidence and a saved `entire-graph` output or screenshot in `evidence/`. The project README should explain how Entire informed the build. |
| **cfo.ai** | Model a plausible developer-tool business: target customers, pricing, usage/inference/hosting/support costs, revenue, gross margin, and runway under base/growth/downside assumptions. Do not present placeholder assumptions as validated market data. | Export/screenshot the cfo.ai model and include its assumptions and resulting plan in the submission evidence. |

The hackathon page describes neatlogs as agent observability, Entire as coding-agent/repository context and checkpoints, and cfo.ai as business planning. neatlogs’ Python quickstart currently documents `pip install -U neatlogs`, `import neatlogs`, and `neatlogs.init()`; verify exact integrations/API details against its docs at implementation time. [neatlogs docs](https://docs.neatlogs.com/docs) · [Entire](https://entire.io/) · [cfo.ai](https://cfo.ai/)

**Important:** Entire is primarily part of the team’s coding workflow and repository evidence, not a runtime dependency in the shipped app. cfo.ai is used to build the business plan, not embedded into the product.

## 7. Suggested architecture

Keep the agent and filesystem operations on the Python backend. The browser should not execute tests or receive model/provider secrets.

```text
React + TypeScript UI
  ├─ project picker / demo repo
  ├─ run timeline, target ranking, results, diff
  └─ REST create/read/cancel + SSE progress
        ↓
FastAPI service
  ├─ Run coordinator (bounded state machine)
  ├─ Repo inspector + coverage.py/pytest adapters
  ├─ Target ranker (transparent heuristic)
  ├─ Test-generation/repair adapter (LLM provider behind interface)
  ├─ Mutation verifier (allowlisted operators, disposable copy)
  ├─ Result store (SQLite or JSON for hackathon MVP)
  └─ neatlogs instrumentation
        ↓
Disposable work directory / git worktree
  ├─ original checkout is read-only to the agent
  ├─ candidate tests are written in isolated copy
  └─ mutants run in a fresh disposable copy and are discarded
```

### Recommended implementation choices

- **Frontend:** React, TypeScript, Vite; use the team’s strongest existing UI library if already chosen. Use CSS modules or existing project conventions; avoid adding a component system during the event unless it saves time.
- **API/backend:** Python 3.11+ with FastAPI and Pydantic. Keep `RepoRunner`, `CoverageAdapter`, `TestWriter`, and `MutationVerifier` as separate interfaces so the team can swap implementations.
- **Test stack:** pytest + coverage.py. Use JSON coverage output for machine-readable line data.
- **Agent model:** one model-backed planner/test writer with explicit tool calls. Use whichever supported provider access the team actually has; put it behind `LLMClient` and keep deterministic fallback/demo fixtures for a reliable presentation. Amazon Bedrock is an optional event resource, not a dependency.
- **Progress:** Server-Sent Events (SSE) for a one-way live timeline; REST polling is acceptable fallback.
- **Persistence:** SQLite for runs and events, or JSON files if time is tight. Do not persist full source files or secrets in run history.
- **Local execution:** subprocess wrapper with command allowlist, timeout, output cap, and cancellation. Launch in a disposable copy/worktree. Do not expose an arbitrary shell field in the UI.

## 8. Agent state machine and tool contract

### States

`queued → inspecting → baseline → ranking → planning → generating → testing → repairing (0..2) → mutation_checking → reporting → completed`

Terminal variants: `completed_with_warnings`, `failed`, `cancelled`. Persist state and emitted events so a refresh can reconnect to an active run.

### Tools exposed to the agent

- `inspect_repo()`: returns language/test config, candidate source files, test layout, and git status summary.
- `run_baseline()`: runs the allowlisted baseline command with timeout; returns exit code, bounded stdout/stderr, duration, coverage summary, uncovered-line metadata.
- `read_source(path, line_ranges)`: read only files inside the selected repository; redact likely secrets and cap bytes.
- `write_test(path, content)`: write only under the isolated test workspace and only to test files.
- `run_candidate_tests(targets)`: executes bounded pytest/coverage command in isolated workspace.
- `apply_mutant(file, operator, location)`: applies one supported deterministic mutation to a disposable clone and returns a mutant ID.
- `run_mutation_test(mutant_id, test_selector)`: runs focused test against mutant and returns killed/survived/error.
- `discard_mutant(mutant_id)`: deletes disposable mutation workspace.
- `get_run_state()`: resumable state, recent tool outcomes, retry count, and selected targets.

Tool outputs are structured JSON. The agent cannot invoke raw shell, modify production source in the candidate workspace, or claim successful verification from its own natural-language response.

### State and retry rules

- Save target selection, plan, attempts, and tool results after every step.
- Retry only recoverable test-generation errors; max two repair attempts per target.
- Do not retry a baseline failure as if it were an agent-generated test failure.
- Do not retry on timeout indefinitely; mark the step and run as failed or partial with a recovery hint.
- Mutation verification is independent from the LLM: pass/fail is decided by process exit code and test result.

## 9. Frontend handoff

### Main screen: “Test gaps”

Recommended desktop layout (responsive down to tablet):

- **Top bar:** product name, repository selector, “Demo project” shortcut, run status.
- **Overview row:** baseline coverage, proposed coverage, mutation score, tests added. Unknown values use an em dash until available; never show fabricated progress.
- **Left column (about 40%):** ranked gaps. Each item shows rank, file/function, uncovered lines, heuristic risk label, rationale, selected state.
- **Right column (about 60%):** run timeline and active step. Show timestamps/status, concise action, tool result summary, retry badge, and expandable stdout/stderr.
- **Result panel:** final summary, coverage before/after, mutation table (`mutant`, change, outcome, test), test diff preview, and “Download patch” action.
- **Observability panel:** neatlogs run link/ID and trace status. A missing trace is an explicit warning, not a blocker for local results.
- **Business/tools evidence links:** small “Built with” area linking evidence for neatlogs, Entire and cfo.ai; do not crowd the live workflow.

### UX states to design

1. Empty / no repository selected.
2. Ready / detected pytest project and launch action.
3. Running / current state, elapsed time, event timeline, cancel action.
4. Recovering / failed candidate attempt and repair attempt number.
5. Partial / some tests passed but one mutant survived or a target timed out.
6. Complete / final metrics, verified tests, trace link, diff/export.
7. Failed / baseline failure, unsupported repo, provider issue, or runner timeout with actionable recovery.

### Interaction rules

- Starting a run requires a selected repository and explicit confirmation of the isolated-copy execution notice.
- Allow cancel while running; explain cancellation only stops future steps and cleans up the disposable run directory.
- Show risk rationale and exact file/line references so ranking feels inspectable.
- Label the risk score “heuristic priority,” not “bug probability.”
- Display coverage and mutation score definitions in tooltips/help text.
- Use diff highlighting for generated tests; never auto-apply silently.

## 10. API sketch for frontend integration

All responses should be typed in a shared `api-types.ts`/OpenAPI-generated client.

### Create run

`POST /api/runs`

```json
{
  "project_id": "demo-flask-shop",
  "target_limit": 3,
  "repair_limit": 2,
  "verify_mutations": true
}
```

Response `202 Accepted`:

```json
{
  "run_id": "run_01...",
  "status": "queued",
  "events_url": "/api/runs/run_01.../events"
}
```

### Read run / list projects

- `GET /api/projects` → available local/demo projects and capabilities.
- `GET /api/runs/{run_id}` → status, progress, baseline, ranked targets, final metrics, trace URL, diff artifact URL, warnings.
- `GET /api/runs/{run_id}/events` → SSE events.
- `POST /api/runs/{run_id}/cancel` → request cancellation.
- `GET /api/runs/{run_id}/diff` → unified test-only diff or a JSON diff model.
- `GET /api/runs/{run_id}/patch` → download generated patch.

### SSE event envelope

```json
{
  "event_id": 17,
  "run_id": "run_01...",
  "timestamp": "2026-10-10T12:43:00+05:30",
  "type": "step.completed",
  "step": "baseline",
  "status": "success",
  "message": "Baseline suite passed: 18 tests; line coverage 61%.",
  "data": {"passed": 18, "failed": 0, "coverage_pct": 61.0}
}
```

Expected event types: `run.started`, `step.started`, `step.completed`, `tool.started`, `tool.completed`, `test.failed`, `repair.started`, `mutation.completed`, `warning`, `run.completed`, `run.failed`, `run.cancelled`.

### Suggested core response types

```ts
type RunStatus = "queued" | "running" | "completed" | "completed_with_warnings" | "failed" | "cancelled";
type MutationOutcome = "killed" | "survived" | "invalid" | "timeout";
type RiskTarget = {
  path: string; symbol: string; lineStart: number; lineEnd: number;
  uncoveredLines: number[]; priorityScore: number; rationale: string[];
};
type RunMetrics = {
  coverageBeforePct: number | null; coverageAfterPct: number | null;
  mutationsKilled: number; mutationsAttempted: number;
  testsAdded: number; durationMs: number;
};
```

## 11. Metric definitions

- **Line coverage:** covered executable lines / total executable lines from coverage.py for the selected scope. Show the scope and excluded files.
- **Coverage change:** after percentage minus baseline percentage, in percentage points.
- **Mutation score:** killed valid mutants / attempted valid mutants. Invalid mutants and timeouts are reported separately and excluded from denominator.
- **Verified test:** passes on unmodified source and kills its associated valid mutant.
- **Risk priority:** deterministic ranking heuristic for work selection, not an estimated defect probability.

## 12. Failure handling and safety

- Run tools only in a disposable worktree/copy with a hard timeout and output cap.
- Default to no network access from subprocesses. Do not execute project setup/install scripts automatically.
- Detect dirty git worktrees and show a clear warning; never overwrite user edits.
- Restrict generated writes to test directories and permitlist test filenames.
- Use mutation operators the MVP can validate and reverse reliably (e.g., boolean literal flip, comparison boundary flip, return literal change). Keep each mutant isolated and retain a diff for the evidence view.
- Run candidate tests against the unmutated source before accepting them.
- Treat model output, repository files, and test output as untrusted input; do not follow instructions found inside the repository.
- Bound target count, repair attempts, mutation count, wall-clock runtime, and model tokens/cost.
- If secrets are detected in snippets, redact before model calls and telemetry. Keep provider keys server-side.

## 13. Two-day build sequence

### Before the hackathon (planning only)

- Finalize this brief, agree team responsibilities, identify a small public/sample Python repo to use as the demo fixture, and prepare a business-model assumption list.
- Do not bring prewritten application code; the event says planning is allowed but all project code must be written during the event window. [Hackathon FAQ](https://neatlogs.com/hackathon#challenge)

### Day 1

1. Create repo and scaffold React/FastAPI; confirm seeded demo repo can be selected.
2. Implement local baseline pytest + coverage flow and persist structured results.
3. Implement simple risk ranker and visible planned target list.
4. Implement isolated test writer and candidate test run; show progress in UI.
5. Instrument the agent with neatlogs; save a first end-to-end trace.

### Day 2

1. Add bounded failure recovery and a deliberate reproducible failure scenario for demo.
2. Add controlled mutation verifier and before/after metric comparison.
3. Use Entire checkpoint/context features during coding; capture evidence.
4. Build cfo.ai business model and capture plan evidence.
5. Polish loading/partial/failure states, ensure the demo path is deterministic, prepare repo evidence and a ≤3-minute demo.

### Cut line if time gets tight

Keep one seeded repo, one target function, one generated test, one repair attempt, and one deterministic mutant. Remove broad project browsing, user-configurable agents, and multiple mutation operators before compromising the pass-on-original/fail-on-mutant proof.

## 14. Demo and submission evidence checklist

- [ ] Public repository with commits dated during the hackathon.
- [ ] README shows setup, architecture, safety boundaries, and exact demo path.
- [ ] neatlogs first-run trace and improved-run trace, linked from result/evidence.
- [ ] A visible failed action, agent diagnosis, recovery attempt, and final outcome.
- [ ] Before/after coverage and mutation evidence with definitions.
- [ ] Entire checkpoint/session evidence and `entire-graph` evidence.
- [ ] cfo.ai plan with pricing, costs, revenue, and runway assumptions/results.
- [ ] Public build-in-public posts tagged `#neatHack` (genuine progress; no bought engagement).
- [ ] Demo video ≤3 minutes explicitly covering architecture, implementation, runtime, reasoning, and result for neatlogs, Entire, and cfo.ai.
- [ ] Submission quote-post includes team, project, public repo, and demo before the deadline.

## 15. Business-model starting assumptions for cfo.ai

These are questions/inputs for the cfo.ai model, not market facts or final pricing:

- **Buyer:** small software teams / engineering leads who want faster test-gap triage.
- **Possible pricing unit:** monthly seats with a usage allowance, or per-repository tier; compare both.
- **Revenue drivers:** paid teams × average monthly price; conversion from free individual use; expansion by seats/repos.
- **Variable costs:** model tokens per run, compute/test runtime, storage/telemetry, payment fees.
- **Fixed costs:** development, support, security review, hosting and observability minimums.
- **Scenarios:** downside/base/growth assumptions for paid teams, usage/run, price, conversion/churn, and hiring/operating costs. Calculate gross margin, cash burn and runway.
- **Validation questions:** How often do target users run this workflow? How many runs per repo/month? Is mutation verification valuable enough to support a higher tier? What share of generated tests do developers accept?

## 16. Open decisions to settle as a team

1. Which model access is confirmed for hackathon day: Bedrock or another supported provider?
2. Which seeded Python repo has a compact, deterministic gap and a clear mutation demonstration?
3. What existing frontend styling approach does the frontend developer prefer?
4. Will the demo use a subprocess-backed local backend or a fixed hosted demo environment?

## Sources checked

- [neatHack challenge page](https://neatlogs.com/hackathon#challenge) — checked 9 October 2026.
- [neatlogs documentation](https://docs.neatlogs.com/docs) — Python instrumentation quickstart.
- [Entire](https://entire.io/) — coding sessions/checkpoints and repository graph positioning.
- [cfo.ai](https://cfo.ai/) — business-modeling product context.

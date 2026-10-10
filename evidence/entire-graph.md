# Entire Graph setup evidence

**Date:** 10 October 2026
**Entire Graph:** v0.4.0
**Repository commit queried:** `700fadd5cd0ea6a353e8ca140ddb7433db303546`

Entire CLI 0.11.4 is enabled for the Codex agent in this repository. The official
Graph plugin is installed and initialized. Session transcript auto-pushing is
disabled (`push_sessions=false`). Codex reports that the seven hooks it installed
still need approval in the Codex app before automatic session checkpoints can run.

## Query performed

```text
entire graph search --repo . --profile full --query \
  "Trace a TestGap LangGraph run with neatlogs and locate the run orchestration and graph invocation code."
```

## Relevant results

- `agent/telemetry.py:langgraph_callbacks` constructs Neatlogs' LangChain callback.
- `services/run_service.py:RunService._execute` attaches the callback to the
  LangGraph stream invocation and consumes node updates.
- `agent/nodes/run_baseline.py:run_baseline` runs pytest and coverage in a
  disposable copy of the selected project.

The query showed the agent orchestration path and its verification boundary
without scanning source files manually first.

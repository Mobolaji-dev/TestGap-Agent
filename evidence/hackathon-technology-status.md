# neatHack required technology evidence

The hackathon requires neatlogs, Entire, and cfo.ai. Their roles differ: neatlogs traces the running agent, Entire supports repository-aware development and checkpoints, and cfo.ai is used to produce the business plan. cfo.ai is not a backend SDK integration.

## neatlogs — runtime tracing

**Implementation:** `agent/telemetry.py` initializes the SDK, attaches the LangGraph callback to graph execution, wraps the OpenAI-compatible LiteLLM client, and flushes telemetry during API shutdown.

**Evidence still needed:** Confirm the deployed run appears in the Neatlogs dashboard and save its trace link or screenshot here. A model-call event in the TestGap API is not, by itself, proof that Neatlogs accepted the trace.

## Entire — repository context and development checkpoints

**Implementation/use:** Entire CLI and Entire Graph are enabled for this repository. `AGENTS.md` directs coding agents to use graph retrieval before code changes. Entire Graph was used to locate the test-writing, verification, run persistence, and patch-serving paths for the verification change.

**Evidence:** See [entire-graph.md](entire-graph.md). Capture an Entire checkpoint view or CLI output for the final demo if available.

## cfo.ai — business plan

**Status: incomplete.** [cfo-ai-model-brief.md](cfo-ai-model-brief.md) is a prompt prepared for cfo.ai; it is not a generated model or evidence of using cfo.ai.

**Action needed:** Run the prompt in cfo.ai, review the assumptions, and save the resulting pricing/cost/revenue/runway model or a screenshot in this directory. Keep speculative inputs labeled as assumptions and replace them with measured usage where available.

## Submission evidence checklist

- [ ] Neatlogs trace link or dashboard screenshot for a complete agent run.
- [ ] Entire graph/checkpoint evidence for the code and development session.
- [ ] cfo.ai business model export or screenshot.
- [ ] Before/after agent results, including baseline and post-candidate coverage; do not claim mutation results until mutation verification exists.

from agent.state import TestGapState


def rank_gaps(state: TestGapState) -> dict:
    """Rank uncovered Python files using a small, inspectable heuristic."""
    files = state.get("baseline_summary", {}).get("files", {})
    targets: list[dict] = []
    for path, file_data in files.items():
        missing = file_data.get("missing_lines", [])
        if not missing:
            continue
        executed = file_data.get("executed_lines", [])
        # More uncovered lines and branches increase triage priority; this is not a bug probability.
        missing_branches = file_data.get("missing_branches", [])
        score = min(100.0, len(missing) * 2.0 + len(missing_branches) * 3.0)
        targets.append(
            {
                "path": path,
                "symbol": "module",
                "line_start": min(missing),
                "line_end": max(missing),
                "uncovered_lines": missing,
                "priority_score": score,
                "rationale": [
                    f"{len(missing)} executable lines are uncovered.",
                    f"{len(missing_branches)} branch paths are uncovered.",
                    "Priority is a transparent triage heuristic, not defect probability.",
                ],
                "executed_line_count": len(executed),
            }
        )
    targets.sort(key=lambda target: target["priority_score"], reverse=True)
    targets = targets[: state.get("target_limit", 3)]
    return {
        "targets": targets,
        "events": [
            {
                "type": "step.completed",
                "step": "ranking",
                "status": "success",
                "message": f"Ranked {len(targets)} under-tested file(s).",
                "data": {"target_count": len(targets)},
            }
        ],
    }

from agent.state import TestGapState, report_progress


def rank_gaps(state: TestGapState) -> dict:
    """Rank uncovered Python files using a small, inspectable heuristic."""
    report_progress(state, step="ranking", message="Ranking under-tested Python files from coverage data.")
    files = state.get("baseline_summary", {}).get("files", {})
    ast_estimate = state.get("baseline_status") == "bootstrap"
    targets: list[dict] = []
    for path, file_data in files.items():
        path_parts = path.replace("\\", "/").split("/")
        filename = path_parts[-1].lower()
        if "tests" in path_parts or "test" in path_parts or filename.startswith("test_"):
            continue
        missing = file_data.get("missing_lines", [])
        if not missing:
            continue
        executed = file_data.get("executed_lines", [])
        # More uncovered lines and branches increase triage priority; this is not a bug probability.
        missing_branches = file_data.get("missing_branches", [])
        score = min(100.0, len(missing) * 2.0 + len(missing_branches) * 3.0)
        if ast_estimate:
            rationale = [
                f"AST found {len(missing)} executable statement lines to consider because coverage was unavailable.",
                "These are candidate lines, not confirmed uncovered lines.",
                "Priority is a transparent triage heuristic, not defect probability.",
            ]
        else:
            rationale = [
                f"{len(missing)} executable lines are uncovered.",
                f"{len(missing_branches)} branch paths are uncovered.",
                "Priority is a transparent triage heuristic, not defect probability.",
            ]
        targets.append(
            {
                "path": path,
                "symbol": "module",
                "line_start": min(missing),
                "line_end": max(missing),
                "uncovered_lines": missing,
                "priority_score": score,
                "coverage_basis": "ast_estimate" if ast_estimate else "measured_coverage",
                "rationale": rationale,
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
                "message": (
                    f"Ranked {len(targets)} AST candidate file(s); measured coverage is unavailable."
                    if ast_estimate
                    else f"Ranked {len(targets)} under-tested file(s)."
                ),
                "data": {"target_count": len(targets)},
            }
        ],
    }

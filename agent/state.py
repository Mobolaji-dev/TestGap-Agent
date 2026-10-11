from collections.abc import Callable
from typing import Any, TypedDict


class AgentEvent(TypedDict, total=False):
    type: str
    step: str
    status: str
    message: str
    data: dict[str, Any]


class TestGapState(TypedDict, total=False):
    run_id: str
    project_id: str
    project_path: str
    repository_url: str | None
    target_limit: int
    run_timeout_seconds: int
    events: list[AgentEvent]
    warnings: list[str]
    targets: list[dict[str, Any]]
    coverage_before_pct: float | None
    coverage_after_pct: float | None
    tests_added: int
    baseline_exit_code: int | None
    baseline_status: str
    baseline_summary: dict[str, Any]
    generated_tests: list[dict[str, Any]]
    progress_callback: Callable[[AgentEvent], None]


def report_progress(
    state: TestGapState,
    *,
    step: str,
    message: str,
    data: dict[str, Any] | None = None,
    event_type: str = "step.started",
) -> None:
    """Persist a stage-start event while a graph node is still working."""
    callback = state.get("progress_callback")
    if callback is not None:
        callback({
            "type": event_type,
            "step": step,
            "status": "running",
            "message": message,
            "data": data or {},
        })

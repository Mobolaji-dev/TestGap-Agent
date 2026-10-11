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

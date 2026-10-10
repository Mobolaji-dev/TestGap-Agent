from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RunStatus = Literal[
    "queued", "running", "completed", "completed_with_warnings", "failed", "cancelled"
]


class CreateRunRequest(BaseModel):
    project_id: str
    target_limit: int = Field(default=3, ge=1, le=10)
    repair_limit: int = Field(default=2, ge=0, le=2)
    verify_mutations: bool = True


class RunEvent(BaseModel):
    event_id: int
    run_id: str
    timestamp: datetime
    type: str
    step: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class RunMetrics(BaseModel):
    coverage_before_pct: float | None = None
    coverage_after_pct: float | None = None
    mutations_killed: int = 0
    mutations_attempted: int = 0
    tests_added: int = 0
    duration_ms: int = 0


class RiskTarget(BaseModel):
    path: str
    symbol: str
    line_start: int
    line_end: int
    uncovered_lines: list[int]
    priority_score: float
    rationale: list[str]


class RunResponse(BaseModel):
    run_id: str
    project_id: str
    status: RunStatus
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list[RunEvent] = Field(default_factory=list)
    targets: list[RiskTarget] = Field(default_factory=list)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    trace_url: str | None = None
    warnings: list[str] = Field(default_factory=list)

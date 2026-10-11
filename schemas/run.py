from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RunStatus = Literal[
    "queued", "running", "completed", "completed_with_warnings", "failed", "cancelled"
]


class CreateRunRequest(BaseModel):
    project_id: str | None = None
    repository_url: str | None = None
    target_limit: int = Field(default=3, ge=1, le=10)
    repair_limit: int = Field(default=2, ge=0, le=2)
    verify_mutations: bool = True

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlsplit

        value = value.strip()
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Only public GitHub HTTPS repository URLs are supported")
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2:
            raise ValueError("Repository URL must have the form https://github.com/owner/repository")
        owner, repository = parts
        if repository.endswith(".git"):
            repository = repository[:-4]
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
        if (
            not owner
            or not repository
            or owner in {".", ".."}
            or repository in {".", ".."}
            or not set(owner) <= allowed
            or not set(repository) <= allowed
        ):
            raise ValueError("GitHub owner and repository names contain unsupported characters")
        return f"https://github.com/{owner}/{repository}.git"

    @model_validator(mode="after")
    def require_project_source(self):
        if bool(self.project_id) == bool(self.repository_url):
            raise ValueError("Provide exactly one of project_id or repository_url")
        return self


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
    coverage_basis: Literal["measured_coverage", "ast_estimate"] = "measured_coverage"
    priority_score: float
    rationale: list[str]


class TestCandidate(BaseModel):
    target_path: str
    test_path: str
    content: str
    model: str
    test_count: int = 0
    verification_status: Literal["pending", "passed", "failed"] = "pending"
    verification_summary: str | None = None


class RunResponse(BaseModel):
    run_id: str
    project_id: str
    repository_url: str | None = None
    status: RunStatus
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list[RunEvent] = Field(default_factory=list)
    targets: list[RiskTarget] = Field(default_factory=list)
    baseline: dict[str, Any] = Field(default_factory=dict)
    candidate_tests: list[TestCandidate] = Field(default_factory=list)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    trace_url: str | None = Field(
        default=None,
        description="Provider trace link when available; Neatlogs traces are searchable by testgap_run_id.",
    )
    warnings: list[str] = Field(default_factory=list)

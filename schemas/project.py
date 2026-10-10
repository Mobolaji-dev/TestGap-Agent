from pathlib import Path

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: str
    name: str
    language: str = "python"
    test_framework: str | None = None
    path_label: str
    ready: bool
    warning: str | None = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class ProjectRecord(BaseModel):
    id: str
    name: str
    path: Path
    test_framework: str | None = None
    repository_url: str | None = None

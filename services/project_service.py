from schemas.project import ProjectRecord, ProjectResponse
from db.repository.project_repository import ProjectRepository


class ProjectNotFoundError(Exception):
    pass


class ProjectService:
    def __init__(self, repository: ProjectRepository | None = None) -> None:
        self.repository = repository or ProjectRepository()

    def list_projects(self) -> dict:
        projects = [self._to_response(record) for record in self.repository.list_projects()]
        return {"projects": projects}

    def get_project(self, project_id: str) -> ProjectRecord:
        project = self.repository.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project '{project_id}' is not configured")
        return project

    @staticmethod
    def _to_response(record: ProjectRecord) -> ProjectResponse:
        ready = record.test_framework == "pytest"
        return ProjectResponse(
            id=record.id,
            name=record.name,
            language="python",
            test_framework=record.test_framework,
            path_label=record.path.name or str(record.path),
            ready=ready,
            warning=None if ready else "pytest was not detected; add pytest before starting a run.",
        )

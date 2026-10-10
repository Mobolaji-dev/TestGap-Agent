from pathlib import Path

from app.config.settings import settings
from schemas.project import ProjectRecord


class ProjectRepository:
    """Read-only registry of projects the agent is allowed to inspect."""

    def list_projects(self) -> list[ProjectRecord]:
        path = settings.repository_path
        if path is None:
            return []
        path = path.expanduser().resolve()
        if not path.is_dir():
            return []

        project_id = self._project_id(path)
        return [
            ProjectRecord(
                id=project_id,
                name=path.name or "Python project",
                path=path,
                test_framework="pytest" if self._has_pytest(path) else None,
            )
        ]

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return next((project for project in self.list_projects() if project.id == project_id), None)

    @staticmethod
    def _project_id(path: Path) -> str:
        return path.name.lower().replace("_", "-").replace(" ", "-") or "workspace"

    @staticmethod
    def _has_pytest(path: Path) -> bool:
        if (path / "pytest.ini").exists():
            return True
        for config_name in ("pyproject.toml", "setup.cfg", "tox.ini"):
            config = path / config_name
            if config.is_file():
                try:
                    if "pytest" in config.read_text(errors="ignore").lower():
                        return True
                except OSError:
                    continue
        for test_dir_name in ("tests", "test"):
            test_dir = path / test_dir_name
            if test_dir.is_dir():
                for test_file in list(test_dir.glob("test_*.py"))[:50]:
                    try:
                        if "pytest" in test_file.read_text(errors="ignore").lower():
                            return True
                    except OSError:
                        continue
        return False

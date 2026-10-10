import asyncio

from app.config.settings import settings
from db.repository.run_repository import RunRepository
from schemas.project import ProjectRecord
from schemas.run import CreateRunRequest
from services.run_service import RunService


def test_scan_persists_baseline_and_ranked_targets(tmp_path):
    project_path = tmp_path / "sample-project"
    (project_path / "tests").mkdir(parents=True)
    (project_path / "app.py").write_text(
        "def choose(value):\n"
        "    if value > 0:\n"
        "        return 'positive'\n"
        "    return 'nonpositive'\n"
    )
    (project_path / "tests" / "test_app.py").write_text(
        "from app import choose\n\n"
        "def test_positive():\n"
        "    assert choose(1) == 'positive'\n"
    )
    repository = RunRepository(tmp_path / "runs.sqlite3")
    service = RunService(repository)
    project = ProjectRecord(
        id="sample-project",
        name="sample-project",
        path=project_path,
        test_framework="pytest",
    )

    async def execute_scan():
        run = await service.create_run(project, CreateRunRequest(project_id=project.id))
        await asyncio.wait_for(
            asyncio.shield(service._tasks[run.run_id]),
            timeout=settings.run_timeout_seconds + 30,
        )
        return service.get_run(run.run_id)

    run = asyncio.run(execute_scan())
    restored = RunRepository(tmp_path / "runs.sqlite3").get(run.run_id)

    assert run.status == "completed"
    assert run.baseline["exit_code"] == 0
    assert run.baseline["coverage_totals"]["percent_covered"] < 100
    assert run.targets[0].path.endswith("app.py")
    assert run.targets[0].uncovered_lines == [4]
    assert [event.type for event in run.events][-1] == "run.completed"
    assert restored == run
    assert project_path.joinpath("app.py").read_text().endswith("return 'nonpositive'\n")

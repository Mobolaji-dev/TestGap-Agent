import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime

from agent.graph import build_graph
from agent.telemetry import langgraph_callbacks
from app.config.settings import settings
from db.repository.run_repository import RunRepository, run_repository
from schemas.project import ProjectRecord
from schemas.run import CreateRunRequest, RunResponse

logger = logging.getLogger(__name__)


class RunNotFoundError(Exception):
    pass


class RunService:
    def __init__(self, repository: RunRepository | None = None) -> None:
        self.repository = repository or run_repository
        self._tasks: dict[str, asyncio.Task] = {}

    async def create_run(self, project: ProjectRecord, payload: CreateRunRequest) -> RunResponse:
        now = datetime.now(UTC)
        run = RunResponse(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            project_id=project.id,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        self.repository.create(run)
        self._event(run.run_id, "run.started", "queued", "Analysis queued.")
        task = asyncio.create_task(self._execute(run.run_id, project, payload))
        self._tasks[run.run_id] = task
        return run

    def get_run(self, run_id: str) -> RunResponse:
        run = self.repository.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    def get_events(self, run_id: str, after_event_id: int = 0):
        events = self.repository.get_events(run_id, after_event_id)
        if events is None:
            raise RunNotFoundError(run_id)
        return events

    def cancel_run(self, run_id: str) -> RunResponse:
        run = self.get_run(run_id)
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        run.status = "cancelled"
        self.repository.save(run)
        self._event(run_id, "run.cancelled", "cancelled", "Cancellation requested.")
        return run

    async def _execute(self, run_id: str, project: ProjectRecord, payload: CreateRunRequest) -> None:
        run = self.get_run(run_id)
        run.status = "running"
        self.repository.save(run)
        started = time.perf_counter()
        try:
            graph = build_graph()
            initial_state = {
                "run_id": run_id,
                "project_id": project.id,
                "project_path": str(project.path),
                "target_limit": payload.target_limit,
                "run_timeout_seconds": settings.run_timeout_seconds,
                "events": [],
                "targets": [],
                "warnings": [],
            }
            callbacks = langgraph_callbacks()
            graph_config = {
                "run_name": f"testgap_{run_id}",
                "metadata": {"testgap_run_id": run_id},
            }
            if callbacks:
                graph_config["callbacks"] = callbacks
            async for update in graph.astream(
                initial_state,
                config=graph_config,
                stream_mode="updates",
            ):
                for node_name, node_result in update.items():
                    if not isinstance(node_result, dict):
                        continue
                    for event_data in node_result.get("events", []):
                        self._event(
                            run_id,
                            event_data["type"],
                            event_data["status"],
                            event_data["message"],
                            step=event_data.get("step", node_name),
                            data=event_data.get("data", {}),
                        )
                    if "targets" in node_result:
                        run.targets = node_result["targets"]
                    if "coverage_before_pct" in node_result:
                        run.metrics.coverage_before_pct = node_result["coverage_before_pct"]
                    if "warnings" in node_result:
                        run.warnings.extend(node_result["warnings"])
                    self.repository.save(run)

            run.status = "completed_with_warnings"
            run.warnings.append(
                "This code slice stops after baseline coverage and gap ranking; test generation and mutation verification are next."
            )
            run.metrics.duration_ms = int((time.perf_counter() - started) * 1000)
            self.repository.save(run)
            self._event(
                run_id,
                "run.completed",
                "completed_with_warnings",
                "Baseline and gap ranking are ready.",
                data={"target_count": len(run.targets)},
            )
        except asyncio.CancelledError:
            run.status = "cancelled"
            self.repository.save(run)
            self._event(run_id, "run.cancelled", "cancelled", "Run cancelled.")
            raise
        except Exception as exc:
            logger.exception("Run %s failed", run_id)
            run.status = "failed"
            run.warnings.append(str(exc))
            run.metrics.duration_ms = int((time.perf_counter() - started) * 1000)
            self.repository.save(run)
            self._event(run_id, "run.failed", "failed", "Analysis failed.", data={"error": str(exc)})

    def _event(
        self,
        run_id: str,
        type: str,
        status: str,
        message: str,
        *,
        step: str = "run",
        data: dict | None = None,
    ) -> None:
        self.repository.append_event(
            run_id, type=type, step=step, status=status, message=message, data=data
        )


_run_service = RunService()


def get_run_service() -> RunService:
    return _run_service

import asyncio
import logging
import queue
import time
import uuid
from datetime import UTC, datetime

from agent.graph import build_graph
from agent.telemetry import langgraph_callbacks
from app.config.settings import settings
from db.repository.run_repository import RunRepository, run_repository
from schemas.project import ProjectRecord
from schemas.run import CreateRunRequest, RiskTarget, RunResponse, TestCandidate

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
        run = self.get_run(run.run_id)
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
        return self.get_run(run_id)

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
            updates: queue.Queue = queue.Queue()
            stream_finished = object()

            def stream_graph() -> None:
                try:
                    for update in graph.stream(
                        initial_state,
                        config=graph_config,
                        stream_mode="updates",
                    ):
                        updates.put(update)
                except BaseException as exc:
                    updates.put(exc)
                finally:
                    updates.put(stream_finished)

            stream_task = asyncio.create_task(asyncio.to_thread(stream_graph))
            while True:
                update = await asyncio.to_thread(updates.get)
                if update is stream_finished:
                    break
                if isinstance(update, BaseException):
                    raise update
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
                    # Event writes persist a fresh copy; reload before applying the node output.
                    run = self.get_run(run_id)
                    if "targets" in node_result:
                        run.targets = [RiskTarget.model_validate(target) for target in node_result["targets"]]
                    if "baseline_summary" in node_result:
                        run.baseline = node_result["baseline_summary"]
                    if "generated_tests" in node_result:
                        run.candidate_tests = [
                            TestCandidate.model_validate(candidate)
                            for candidate in node_result["generated_tests"]
                        ]
                    if "coverage_before_pct" in node_result:
                        run.metrics.coverage_before_pct = node_result["coverage_before_pct"]
                    if "warnings" in node_result:
                        run.warnings.extend(node_result["warnings"])
                    self.repository.save(run)
            await stream_task

            baseline_exit_code = run.baseline.get("exit_code")
            if baseline_exit_code != 0:
                run.status = "failed"
                completion_message = "Baseline pytest failed; gap ranking was skipped."
                completion_event = "run.failed"
            elif run.metrics.coverage_before_pct is None:
                run.status = "completed_with_warnings"
                completion_message = "Baseline passed, but coverage data is unavailable."
                completion_event = "run.completed"
            else:
                run.status = "completed"
                completion_message = "Baseline coverage and gap ranking are ready."
                completion_event = "run.completed"
            if run.warnings and run.status == "completed":
                run.status = "completed_with_warnings"
                completion_message = "Scan completed with warnings; review the run details."
            run.metrics.duration_ms = int((time.perf_counter() - started) * 1000)
            self.repository.save(run)
            self._event(
                run_id,
                completion_event,
                run.status,
                completion_message,
                data={"target_count": len(run.targets), "coverage_pct": run.metrics.coverage_before_pct},
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

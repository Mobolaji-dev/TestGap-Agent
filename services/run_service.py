import asyncio
import difflib
import logging
import queue
import shutil
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from agent.graph import build_graph
from agent.telemetry import langgraph_callbacks, neatlogs_status
from app.config.settings import settings
from db.repository.project_repository import ProjectRepository
from db.repository.run_repository import RunRepository, run_repository
from schemas.project import ProjectRecord
from schemas.run import CreateRunRequest, RiskTarget, RunResponse, TestCandidate

logger = logging.getLogger(__name__)


class RunNotFoundError(Exception):
    pass


class TestPatchUnavailableError(Exception):
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
            repository_url=project.repository_url,
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

    def get_test_patch(self, run_id: str, project: ProjectRecord | None = None) -> str:
        run = self.get_run(run_id)
        stored_patch = self.repository.get_patch(run_id)
        if stored_patch is not None:
            return stored_patch
        if not run.candidate_tests:
            raise TestPatchUnavailableError(run_id)
        if any(candidate.verification_status != "passed" for candidate in run.candidate_tests):
            raise TestPatchUnavailableError(run_id)
        if project is None or run.project_id != project.id:
            raise TestPatchUnavailableError(run_id)

        return self._build_test_patch(run, project)

    @staticmethod
    def _build_test_patch(run: RunResponse, project: ProjectRecord) -> str:
        root = project.path.resolve(strict=True)
        chunks: list[str] = []
        for candidate in run.candidate_tests:
            relative = PurePosixPath(candidate.test_path)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or relative.suffix != ".py"
                or not relative.parts
            ):
                raise TestPatchUnavailableError(run.run_id)

            test_path = (root / Path(*relative.parts)).resolve()
            try:
                test_path.relative_to(root)
            except ValueError as exc:
                raise TestPatchUnavailableError(run.run_id) from exc

            if test_path.exists() and (not test_path.is_file() or test_path.is_symlink()):
                raise TestPatchUnavailableError(run.run_id)
            original = test_path.read_text().splitlines(keepends=True) if test_path.exists() else []
            proposed = candidate.content.splitlines(keepends=True)
            if proposed and not proposed[-1].endswith(("\n", "\r")):
                proposed[-1] += "\n"
            fromfile = f"a/{relative.as_posix()}" if original else "/dev/null"
            chunks.extend(
                difflib.unified_diff(
                    original,
                    proposed,
                    fromfile=fromfile,
                    tofile=f"b/{relative.as_posix()}",
                )
            )
        return "".join(chunks)

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
            telemetry = neatlogs_status()
            if not telemetry["initialized"]:
                detail = str(telemetry["status"])
                warning = f"Neatlogs tracing is unavailable ({detail}); this run will not appear in Neatlogs."
                self._event(
                    run_id,
                    "telemetry.disabled",
                    "warning",
                    warning,
                    step="telemetry",
                    data={"configured": telemetry["configured"], "status": detail},
                )
            else:
                self._event(
                    run_id,
                    "telemetry.enabled",
                    "success",
                    "Neatlogs tracing is initialized for this run.",
                    step="telemetry",
                    data={"endpoint": telemetry["endpoint"]},
                )
            if project.repository_url:
                workspace_root = ProjectRepository.get_workspace_root()
                project.path = workspace_root / run.run_id / project.name
                self._event(
                    run_id,
                    "step.started",
                    "running",
                    "Checking GitHub and creating a shallow clone (up to 180 seconds).",
                    step="clone",
                    data={
                        "repository_url": project.repository_url,
                        "phase": "github_metadata_and_shallow_clone",
                        "timeout_seconds": min(settings.repository_clone_timeout_seconds, 180),
                    },
                )
                await asyncio.to_thread(
                    ProjectRepository.clone_repository,
                    project.repository_url,
                    project.path,
                )
                project.test_framework = (
                    "pytest" if ProjectRepository._has_pytest(project.path) else None
                )
                self._event(
                    run_id,
                    "step.completed",
                    "success",
                    f"Cloned {project.name} from GitHub.",
                    step="clone",
                    data={"test_framework": project.test_framework},
                )
            graph = build_graph()
            updates: queue.Queue = queue.Queue()
            stream_finished = object()

            def publish(update) -> None:
                updates.put(update)

            def publish_progress(event_data: dict) -> None:
                # Persist events on the asyncio thread; the graph worker only
                # forwards messages so SQLite writes never race each other.
                publish(("progress", event_data))

            initial_state = {
                "run_id": run_id,
                "project_id": project.id,
                "project_path": str(project.path),
                "repository_url": project.repository_url,
                "target_limit": payload.target_limit,
                "repair_limit": payload.repair_limit,
                "run_timeout_seconds": settings.run_timeout_seconds,
                "events": [],
                "targets": [],
                "warnings": [],
                "progress_callback": publish_progress,
            }
            callbacks = langgraph_callbacks()
            graph_config = {
                "run_name": f"testgap_{run_id}",
                "metadata": {"testgap_run_id": run_id},
            }
            if callbacks:
                graph_config["callbacks"] = callbacks
            def stream_graph() -> None:
                try:
                    for update in graph.stream(
                        initial_state,
                        config=graph_config,
                        stream_mode="updates",
                    ):
                        publish(update)
                except BaseException as exc:
                    publish(exc)
                finally:
                    publish(stream_finished)

            stream_thread = threading.Thread(
                target=stream_graph,
                name=f"testgap-graph-{run_id}",
                daemon=True,
            )
            stream_thread.start()
            while True:
                try:
                    update = updates.get_nowait()
                except queue.Empty:
                    # Keep the API loop responsive while the graph worker runs;
                    # polling avoids occupying a second executor thread for a
                    # blocking queue read and still persists each event promptly.
                    await asyncio.sleep(0.02)
                    continue
                if update is stream_finished:
                    break
                if isinstance(update, tuple) and update[0] == "progress":
                    event_data = update[1]
                    self._event(
                        run_id,
                        event_data["type"],
                        event_data["status"],
                        event_data["message"],
                        step=event_data["step"],
                        data=event_data.get("data", {}),
                    )
                    continue
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
                    if "coverage_after_pct" in node_result:
                        run.metrics.coverage_after_pct = node_result["coverage_after_pct"]
                    if "tests_added" in node_result:
                        run.metrics.tests_added = node_result["tests_added"]
                    if "warnings" in node_result:
                        run.warnings.extend(node_result["warnings"])
                    self.repository.save(run)
            run = self.get_run(run_id)
            if run.candidate_tests and all(
                candidate.verification_status == "passed" for candidate in run.candidate_tests
            ):
                self.repository.save_patch(run_id, self._build_test_patch(run, project))

            baseline_status = run.baseline.get("baseline_status", "failed")
            if baseline_status == "failed":
                run.status = "failed"
                completion_message = "Baseline pytest failed; gap ranking was skipped."
                completion_event = "run.failed"
            elif baseline_status == "no_python_source":
                run.status = "completed_with_warnings"
                completion_message = "No tests or testable Python source were found; no tests could be drafted."
                completion_event = "run.completed"
            elif run.metrics.coverage_before_pct is None:
                run.status = "completed_with_warnings"
                completion_message = "Baseline completed, but coverage data is unavailable."
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
                data={
                    "target_count": len(run.targets),
                    "coverage_before_pct": run.metrics.coverage_before_pct,
                    "coverage_after_pct": run.metrics.coverage_after_pct,
                    "tests_added": run.metrics.tests_added,
                },
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
        finally:
            if project.repository_url:
                shutil.rmtree(project.path.parent, ignore_errors=True)

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

from datetime import UTC, datetime

from schemas.run import RunEvent, RunResponse


class RunRepository:
    """Process-local run store for the hackathon MVP; replace with durable storage later."""

    def __init__(self) -> None:
        self._runs: dict[str, RunResponse] = {}

    def create(self, run: RunResponse) -> RunResponse:
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RunResponse | None:
        return self._runs.get(run_id)

    def save(self, run: RunResponse) -> RunResponse:
        run.updated_at = datetime.now(UTC)
        self._runs[run.run_id] = run
        return run

    def append_event(
        self,
        run_id: str,
        *,
        type: str,
        step: str,
        status: str,
        message: str,
        data: dict | None = None,
    ) -> RunEvent:
        run = self._runs[run_id]
        event = RunEvent(
            event_id=(run.events[-1].event_id + 1) if run.events else 1,
            run_id=run_id,
            timestamp=datetime.now(UTC),
            type=type,
            step=step,
            status=status,
            message=message,
            data=data or {},
        )
        run.events.append(event)
        run.current_step = step
        self.save(run)
        return event

    def get_events(self, run_id: str, after_event_id: int = 0) -> list[RunEvent] | None:
        run = self.get(run_id)
        if run is None:
            return None
        return [event for event in run.events if event.event_id > after_event_id]


run_repository = RunRepository()

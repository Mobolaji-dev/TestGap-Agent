import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import settings
from schemas.run import RunEvent, RunResponse


class RunRepository:
    """SQLite-backed run and event store for API results across process restarts."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path or settings.run_database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS patches (run_id TEXT PRIMARY KEY, patch TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _serialize(run: RunResponse) -> str:
        return run.model_dump_json()

    def _write(self, run: RunResponse) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO runs (run_id, payload) VALUES (?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET payload = excluded.payload",
                (run.run_id, self._serialize(run)),
            )

    def create(self, run: RunResponse) -> RunResponse:
        self._write(run)
        return run

    def get(self, run_id: str) -> RunResponse | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return RunResponse.model_validate_json(row["payload"]) if row else None

    def save_patch(self, run_id: str, patch: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO patches (run_id, patch) VALUES (?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET patch = excluded.patch",
                (run_id, patch),
            )

    def get_patch(self, run_id: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT patch FROM patches WHERE run_id = ?", (run_id,)
            ).fetchone()
        return row["patch"] if row else None

    def save(self, run: RunResponse) -> RunResponse:
        run.updated_at = datetime.now(UTC)
        self._write(run)
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
        run = self.get(run_id)
        if run is None:
            raise KeyError(f"Run {run_id} does not exist")
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

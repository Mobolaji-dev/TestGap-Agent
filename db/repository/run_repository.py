import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import settings
from schemas.run import RunEvent, RunResponse


logger = logging.getLogger(__name__)


class RunRepository:
    """Persist run records in PostgreSQL, or SQLite for local development."""

    def __init__(
        self,
        database_path: Path | str | None = None,
        database_url: str | None = None,
    ) -> None:
        self._pool = None
        configured_url = database_url
        if configured_url is None and database_path is None and settings.database_url:
            configured_url = settings.database_url.get_secret_value()

        if configured_url:
            self.backend = "postgresql"
            self.persistent = True
            self.database_path = None
            self.database_url = self._normalize_database_url(configured_url)
            self._open_postgres()
            self._init_db()
            return

        self.backend = "sqlite"
        self.persistent = False
        self.database_url = None
        target_path = Path(database_path or settings.run_database_path).expanduser()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            self.database_path = target_path
            self._init_db()
        except (OSError, sqlite3.OperationalError) as exc:
            fallback_dir = Path("/tmp/testgap-runs")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.database_path = fallback_dir / target_path.name
            logger.warning(
                "Could not initialize SQLite at %s (%s); using ephemeral fallback %s",
                target_path,
                exc,
                self.database_path,
            )
            self._init_db()

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        if database_url.startswith("postgres://"):
            return "postgresql://" + database_url.removeprefix("postgres://")
        return database_url

    def _open_postgres(self) -> None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(
            conninfo=self.database_url,
            min_size=1,
            max_size=8,
            timeout=10,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        self._pool.open(wait=True, timeout=10)

    def _init_db(self) -> None:
        with self._connection() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS patches (run_id TEXT PRIMARY KEY, patch TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        if self._pool is not None:
            raise RuntimeError("PostgreSQL connections are managed by the connection pool")
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        if self._pool is not None:
            with self._pool.connection() as connection:
                yield connection
            return

        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _sql(self, statement: str) -> str:
        return statement.replace("?", "%s") if self._pool is not None else statement

    def health(self) -> dict[str, bool | str]:
        try:
            with self._connection() as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception:
            return {
                "backend": self.backend,
                "persistent": self.persistent,
                "connected": False,
            }
        return {
            "backend": self.backend,
            "persistent": self.persistent,
            "connected": True,
        }

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()

    @staticmethod
    def _serialize(run: RunResponse) -> str:
        return run.model_dump_json()

    def _write(self, run: RunResponse) -> None:
        with self._connection() as connection:
            connection.execute(
                self._sql(
                    "INSERT INTO runs (run_id, payload) VALUES (?, ?) "
                    "ON CONFLICT(run_id) DO UPDATE SET payload = excluded.payload"
                ),
                (run.run_id, self._serialize(run)),
            )

    def create(self, run: RunResponse) -> RunResponse:
        self._write(run)
        return run

    def get(self, run_id: str) -> RunResponse | None:
        with self._connection() as connection:
            row = connection.execute(
                self._sql("SELECT payload FROM runs WHERE run_id = ?"), (run_id,)
            ).fetchone()
        return RunResponse.model_validate_json(row["payload"]) if row else None

    def save_patch(self, run_id: str, patch: str) -> None:
        with self._connection() as connection:
            connection.execute(
                self._sql(
                    "INSERT INTO patches (run_id, patch) VALUES (?, ?) "
                    "ON CONFLICT(run_id) DO UPDATE SET patch = excluded.patch"
                ),
                (run_id, patch),
            )

    def get_patch(self, run_id: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                self._sql("SELECT patch FROM patches WHERE run_id = ?"), (run_id,)
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

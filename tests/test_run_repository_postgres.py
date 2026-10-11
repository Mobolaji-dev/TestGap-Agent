import sqlite3
import sys
import types
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import Settings
from db.repository.run_repository import RunRepository
from schemas.run import RunResponse


class _Cursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class _FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    def execute(self, statement, params=()):
        self.pool.statements.append(statement)
        if statement.startswith("INSERT INTO runs"):
            self.pool.runs[params[0]] = params[1]
        elif statement.startswith("SELECT payload FROM runs"):
            payload = self.pool.runs.get(params[0])
            return _Cursor({"payload": payload} if payload is not None else None)
        elif statement.startswith("INSERT INTO patches"):
            self.pool.patches[params[0]] = params[1]
        elif statement.startswith("SELECT patch FROM patches"):
            patch = self.pool.patches.get(params[0])
            return _Cursor({"patch": patch} if patch is not None else None)
        return _Cursor({"result": 1})


class _FakePool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.runs = {}
        self.patches = {}
        self.statements = []
        self.closed = False

    def open(self, *, wait, timeout):
        assert wait is True
        assert timeout == 10

    @contextmanager
    def connection(self):
        yield _FakeConnection(self)

    def close(self):
        self.closed = True


def test_postgres_repository_persists_runs_events_and_patches(monkeypatch):
    pool_module = types.ModuleType("psycopg_pool")
    pool_module.ConnectionPool = _FakePool
    psycopg_module = types.ModuleType("psycopg")
    psycopg_module.__path__ = []
    rows_module = types.ModuleType("psycopg.rows")
    rows_module.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", psycopg_module)
    monkeypatch.setitem(sys.modules, "psycopg.rows", rows_module)
    monkeypatch.setitem(sys.modules, "psycopg_pool", pool_module)

    repository = RunRepository(database_url="postgres://user:password@db.example/testgap")
    now = datetime.now(UTC)
    run = RunResponse(
        run_id="run_postgres_test",
        project_id="github-demo",
        status="queued",
        created_at=now,
        updated_at=now,
    )
    repository.create(run)
    event = repository.append_event(
        run.run_id,
        type="step.started",
        step="baseline",
        status="running",
        message="Baseline started.",
    )
    repository.save_patch(run.run_id, "diff --git a/test.py b/test.py")

    restored = repository.get(run.run_id)
    assert repository.backend == "postgresql"
    assert repository.persistent is True
    assert repository.health() == {
        "backend": "postgresql",
        "persistent": True,
        "connected": True,
    }
    assert restored is not None
    assert restored.events[0] == event
    assert repository.get_events(run.run_id) == [event]
    assert repository.get_patch(run.run_id) == "diff --git a/test.py b/test.py"
    assert repository._pool.kwargs["conninfo"].startswith("postgresql://")
    assert any("VALUES (%s, %s)" in query for query in repository._pool.statements)

    pool = repository._pool
    repository.close()
    assert pool.closed is True


def test_database_url_accepts_render_standard_environment_variable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@db.example/testgap")

    settings = Settings(_env_file=None)

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value().startswith("postgresql://")


def test_readonly_sqlite_path_falls_back_to_temporary_storage(monkeypatch, tmp_path):
    requested_path = tmp_path / f"{tmp_path.name}.sqlite3"
    initialize = RunRepository._init_db

    def fail_for_requested_path(repository):
        if repository.database_path == requested_path:
            raise sqlite3.OperationalError("attempt to write a readonly database")
        initialize(repository)

    monkeypatch.setattr(RunRepository, "_init_db", fail_for_requested_path)
    repository = RunRepository(database_path=requested_path)

    assert repository.database_path == Path("/tmp/testgap-runs") / requested_path.name
    assert repository.persistent is False

    repository.database_path.unlink(missing_ok=True)

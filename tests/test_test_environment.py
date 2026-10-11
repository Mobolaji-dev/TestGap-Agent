import sys

import pytest

from agent.test_environment import (
    TestEnvironmentError as _TestEnvironmentError,
    _example_settings,
    _requirements,
    prepare_test_environment,
)


def test_example_settings_uses_dummy_values_not_template_secrets(tmp_path):
    (tmp_path / ".env.example").write_text(
        "DATABASE_URL=postgresql://real-looking-value\n"
        "SECRET_KEY=example-secret-value\n"
        "SUPABASE_URL=https://service.example.test\n"
    )

    env = _example_settings(tmp_path)

    assert env["DATABASE_URL"] == "postgresql+asyncpg://testgap:testgap@127.0.0.1:5432/testgap"
    assert env["SECRET_KEY"] == "testgap-placeholder-not-a-real-secret"
    assert env["SUPABASE_URL"] == "http://127.0.0.1"
    assert "example-secret-value" not in env.values()


def test_requirements_rejects_direct_urls_and_pip_options(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("package==1.2.3\nhttps://example.test/package.whl\n")

    with pytest.raises(_TestEnvironmentError, match="direct URL"):
        _requirements(tmp_path)


def test_repository_without_requirements_uses_scrubbed_runtime(tmp_path):
    (tmp_path / ".env.example").write_text("SECRET_KEY=real-looking-value\n")

    runner, env, metadata = prepare_test_environment(tmp_path, timeout_seconds=30)

    assert str(runner) == sys.executable
    assert metadata["status"] == "no_requirements_manifest"
    assert env["SECRET_KEY"] == "testgap-placeholder-not-a-real-secret"
    assert "real-looking-value" not in env.values()

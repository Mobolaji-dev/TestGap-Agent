from agent.nodes import verify_tests as verification
from agent.nodes.verify_tests import _verification_diagnostic
from schemas.run import TestCandidate as RunTestCandidate


def test_verification_diagnostic_captures_failure_and_scrubs_workspace(tmp_path):
    stdout = tmp_path / "stdout.txt"
    stderr = tmp_path / "stderr.txt"
    stdout.write_text("E   ModuleNotFoundError: app.services.auth\n")
    stderr.write_text(f"File \"{tmp_path}/copy/tests/test_generated.py\", line 1\n")

    diagnostic = _verification_diagnostic(stdout, stderr, tmp_path)

    assert "ModuleNotFoundError: app.services.auth" in diagnostic
    assert str(tmp_path) not in diagnostic
    assert "<temporary-run-dir>/copy/tests/test_generated.py" in diagnostic


def test_verification_repairs_candidate_within_requested_budget(tmp_path, monkeypatch):
    attempts = iter([
        (False, "pytest failed", "AssertionError: expected 200, got 404", None),
        (True, None, None, 66.7),
    ])
    monkeypatch.setattr(verification, "_run_candidate", lambda *args, **kwargs: next(attempts))
    monkeypatch.setattr(
        verification,
        "_repair_candidate",
        lambda state, item, diagnostic, attempt: {
            **item,
            "content": "def test_repaired():\n    assert True\n",
        },
    )
    candidate = {
        "target_path": "app/api/auth.py",
        "test_path": "tests/test_auth_testgap.py",
        "content": "def test_original():\n    assert False\n",
        "model": "claude-haiku",
    }

    result = verification.verify_tests({
        "project_path": str(tmp_path),
        "generated_tests": [candidate],
        "repair_limit": 1,
        "baseline_summary": {"test_environment": {"status": "ready"}},
    })

    assert result["tests_added"] == 1
    assert result["coverage_after_pct"] == 66.7
    assert result["generated_tests"][0]["verification_status"] == "passed"
    assert result["generated_tests"][0]["repair_attempts"] == 1
    assert result["generated_tests"][0]["repair_status"] == "succeeded"
    assert result["warnings"] == []


def test_verification_reports_failed_model_repair_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(
        verification,
        "_run_candidate",
        lambda *args, **kwargs: (False, "pytest failed", "404 Not Found", None),
    )
    monkeypatch.setattr(verification, "_repair_candidate", lambda *args, **kwargs: None)
    candidate = {
        "target_path": "app/api/auth.py",
        "test_path": "tests/test_auth_testgap.py",
        "content": "def test_wrong_route():\n    assert False\n",
        "model": "claude-haiku",
    }

    result = verification.verify_tests({
        "project_path": str(tmp_path),
        "generated_tests": [candidate],
        "repair_limit": 2,
        "baseline_summary": {"test_environment": {"status": "ready"}},
    })

    rejected = result["generated_tests"][0]
    assert rejected["verification_status"] == "failed"
    assert rejected["repair_attempts"] == 1
    assert rejected["repair_status"] == "failed"
    assert "Model repair failed" in rejected["verification_summary"]
    assert rejected["repair_failure"] == "model repair returned no result"


def test_api_candidate_schema_preserves_repair_diagnostics():
    candidate = RunTestCandidate.model_validate({
        "target_path": "app/api/auth.py",
        "test_path": "tests/test_auth_testgap.py",
        "content": "def test_route():\n    assert True\n",
        "model": "claude-haiku",
        "repair_attempts": 1,
        "repair_status": "failed",
        "repair_failure": "model request failed (APITimeoutError)",
    })

    assert candidate.repair_status == "failed"
    assert candidate.repair_failure == "model request failed (APITimeoutError)"


def test_repair_candidate_parses_markdown_wrapped_code(tmp_path, monkeypatch):
    target_file = tmp_path / "app.py"
    target_file.write_text("def choose(x): return x > 0\n")

    repaired_code = (
        "Here is the repaired test:\n```python\n"
        "from app import choose\n\n"
        "def test_choose():\n"
        "    assert choose(1) is True\n"
        "```\nFixed the unconfigured mock."
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class FakeChoice:
                        message = type("Msg", (), {"content": repaired_code})()
                        finish_reason = "stop"
                    class FakeResp:
                        choices = [FakeChoice()]
                        usage = None
                    return FakeResp()

    monkeypatch.setattr(verification, "OpenAI", FakeClient)
    from pydantic import SecretStr
    monkeypatch.setattr(verification.settings, "litellm_api_key", SecretStr("test-key"))

    state = {
        "project_path": str(tmp_path),
        "run_id": "run-test",
    }
    item = {
        "target_path": "app.py",
        "test_path": "tests/test_app.py",
        "content": "def test_choose(): assert False\n",
    }

    repaired = verification._repair_candidate(state, item, "AssertionError", 1)
    assert repaired is not None
    assert "_repair_error" not in repaired
    assert repaired["test_count"] == 1
    assert "def test_choose():" in repaired["content"]
    assert "Here is the repaired test" not in repaired["content"]


def test_repair_candidate_handles_invalid_python_gracefully(tmp_path, monkeypatch):
    target_file = tmp_path / "app.py"
    target_file.write_text("def choose(x): return x > 0\n")

    invalid_code = "def test_broken(:\n    assert True"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class FakeChoice:
                        message = type("Msg", (), {"content": invalid_code})()
                        finish_reason = "stop"
                    class FakeResp:
                        choices = [FakeChoice()]
                        usage = None
                    return FakeResp()

    monkeypatch.setattr(verification, "OpenAI", FakeClient)
    from pydantic import SecretStr
    monkeypatch.setattr(verification.settings, "litellm_api_key", SecretStr("test-key"))

    state = {
        "project_path": str(tmp_path),
        "run_id": "run-test",
    }
    item = {
        "target_path": "app.py",
        "test_path": "tests/test_app.py",
        "content": "def test_choose(): assert False\n",
    }

    repaired = verification._repair_candidate(state, item, "AssertionError", 1)
    assert repaired is not None
    assert "_repair_error" in repaired
    assert "model repair rejected" in repaired["_repair_error"]


def test_repair_candidate_salvages_truncated_output(tmp_path, monkeypatch):
    target_file = tmp_path / "app.py"
    target_file.write_text("def choose(x): return x > 0\n")

    truncated_code = (
        "```python\n"
        "def test_one():\n"
        "    assert 1 == 1\n\n"
        "def test_two():\n"
        "    assert 2 =="
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class FakeChoice:
                        message = type("Msg", (), {"content": truncated_code})()
                        finish_reason = "length"
                    class FakeResp:
                        choices = [FakeChoice()]
                        usage = None
                    return FakeResp()

    monkeypatch.setattr(verification, "OpenAI", FakeClient)
    from pydantic import SecretStr
    monkeypatch.setattr(verification.settings, "litellm_api_key", SecretStr("test-key"))

    state = {
        "project_path": str(tmp_path),
        "run_id": "run-test",
    }
    item = {
        "target_path": "app.py",
        "test_path": "tests/test_app.py",
        "content": "def test_one(): assert False\n",
    }

    repaired = verification._repair_candidate(state, item, "AssertionError", 1)
    assert repaired is not None
    assert "_repair_error" not in repaired
    assert repaired["test_count"] == 1
    assert "def test_one():" in repaired["content"]
    assert "test_two" not in repaired["content"]


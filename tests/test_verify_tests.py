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

from agent.nodes.verify_tests import _verification_diagnostic


def test_verification_diagnostic_captures_failure_and_scrubs_workspace(tmp_path):
    stdout = tmp_path / "stdout.txt"
    stderr = tmp_path / "stderr.txt"
    stdout.write_text("E   ModuleNotFoundError: app.services.auth\n")
    stderr.write_text(f"File \"{tmp_path}/copy/tests/test_generated.py\", line 1\n")

    diagnostic = _verification_diagnostic(stdout, stderr, tmp_path)

    assert "ModuleNotFoundError: app.services.auth" in diagnostic
    assert str(tmp_path) not in diagnostic
    assert "<temporary-run-dir>/copy/tests/test_generated.py" in diagnostic

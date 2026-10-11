from types import SimpleNamespace

from agent.nodes import run_baseline as baseline_module


def test_passing_tests_fall_back_to_ast_when_coverage_json_is_missing(tmp_path, monkeypatch):
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "app.py").write_text("def choose(value):\n    return value\n")

    calls = 0

    def fake_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="coverage report unavailable")

    monkeypatch.setattr(baseline_module.subprocess, "run", fake_run)

    result = baseline_module.run_baseline({"project_path": str(project_path)})

    assert result["baseline_exit_code"] == 0
    assert result["baseline_status"] == "bootstrap"
    assert result["baseline_summary"]["baseline_mode"] == "coverage_fallback"
    assert result["baseline_summary"]["coverage_totals"]["percent_covered"] is None
    assert any(path.endswith("app.py") for path in result["baseline_summary"]["files"])
    assert "continuing with AST-based candidates" in result["warnings"][0]

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent.test_environment import (
    TestEnvironmentError,
    dependency_setup_timeout,
    fallback_test_environment,
    prepare_test_environment,
)
from agent.state import TestGapState, report_progress


def _static_python_files(root: Path, ignored: set[str]) -> tuple[dict[str, dict], int]:
    """Return AST statement lines as uncovered candidates when pytest has no tests."""
    files: dict[str, dict] = {}
    parse_failures = 0
    for source_path in root.rglob("*.py"):
        relative = source_path.relative_to(root)
        if any(part in ignored or part in {"tests", "test"} for part in relative.parts):
            continue
        if source_path.is_symlink() or source_path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(source_path.read_text(errors="replace"), filename=str(source_path))
        except (OSError, SyntaxError, UnicodeError):
            parse_failures += 1
            continue
        statement_lines = sorted({
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.stmt) and hasattr(node, "lineno")
        })
        if statement_lines:
            files[str(source_path)] = {
                "executed_lines": [],
                "missing_lines": statement_lines,
                "missing_branches": [],
            }
    return files, parse_failures


def _is_environment_collection_failure(output: str) -> bool:
    """Identify collection failures caused by missing project setup, not test assertions."""
    return (
        "ModuleNotFoundError: No module named" in output
        or ("ValidationError" in output and "Field required" in output)
    )


def run_baseline(state: TestGapState) -> dict:
    report_progress(
        state,
        step="baseline",
        message="Preparing the isolated test environment and running the existing pytest suite.",
    )
    root = Path(state["project_path"]).resolve(strict=True)
    baseline_timeout = max(5, min(int(state.get("run_timeout_seconds", 90)), 180))
    ignored = {
        ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
        ".aws", ".ssh", ".config", ".coverage",
    }
    with tempfile.TemporaryDirectory(prefix="testgap-baseline-") as temp_dir:
        workspace = Path(temp_dir) / root.name

        def ignore_entries(directory: str, names: list[str]) -> set[str]:
            return {
                name
                for name in names
                if name in ignored
                or name == ".env"
                or name.startswith(".env.")
                or (Path(directory) / name).is_symlink()
            }

        shutil.copytree(root, workspace, ignore=ignore_entries, symlinks=False)
        coverage_file = Path(temp_dir) / "coverage.json"
        stdout_path = Path(temp_dir) / "pytest.stdout"
        stderr_path = Path(temp_dir) / "pytest.stderr"
        test_environment = {"status": "not_prepared"}
        setup_warning = None
        runner = Path(sys.executable)
        if state.get("repository_url"):
            try:
                setup_timeout = dependency_setup_timeout(baseline_timeout)
                report_progress(
                    state,
                    step="baseline",
                    event_type="step.progress",
                    message=f"Installing the repository's declared test dependencies (up to {setup_timeout} seconds on a cold run).",
                    data={"phase": "dependency_setup", "timeout_seconds": setup_timeout},
                )
                runner, child_env, test_environment = prepare_test_environment(
                    root,
                    timeout_seconds=baseline_timeout,
                )
                report_progress(
                    state,
                    step="baseline",
                    event_type="step.progress",
                    message=f"Dependency setup finished; running pytest baseline (up to {baseline_timeout} seconds).",
                    data={"phase": "pytest", "timeout_seconds": baseline_timeout},
                )
            except TestEnvironmentError as exc:
                setup_warning = str(exc)
                test_environment = {"status": "failed", "reason": setup_warning}
                child_env = fallback_test_environment(root, Path(temp_dir))
                report_progress(
                    state,
                    step="baseline",
                    event_type="step.progress",
                    message="Dependency setup failed; trying pytest with scanner-provided packages and project placeholders.",
                    data={"phase": "environment_fallback"},
                )
        else:
            child_env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": temp_dir,
                "PYTHONPATH": os.pathsep.join((str(workspace), str(workspace / "src"))),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            if "SYSTEMROOT" in os.environ:
                child_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        child_env["PYTHONPATH"] = os.pathsep.join((str(workspace), str(workspace / "src")))
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            result = subprocess.run(
                [
                    str(runner), "-m", "coverage", "run", "--branch", "-m", "pytest",
                    "-q", "-p", "no:cacheprovider",
                ],
                cwd=workspace,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=baseline_timeout,
                check=False,
                shell=False,
                env=child_env,
            )
        summary: dict = {
            **state.get("baseline_summary", {}),
            "command": "python -m coverage run --branch -m pytest -q",
            "test_environment": test_environment,
            "exit_code": result.returncode,
            "stdout": stdout_path.read_bytes()[-8000:].decode(errors="replace"),
            "stderr": stderr_path.read_bytes()[-8000:].decode(errors="replace"),
        }
        warning = None
        coverage_pct = None
        baseline_status = "passed"
        if result.returncode == 0:
            report = subprocess.run(
                [str(runner), "-m", "coverage", "json", "-o", str(coverage_file)],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=baseline_timeout,
                check=False,
                shell=False,
                env=child_env,
            )
            if report.returncode == 0 and coverage_file.exists():
                data = json.loads(coverage_file.read_text())
                totals = data.get("totals", {})
                coverage_pct = totals.get("percent_covered")
                summary["coverage_totals"] = totals
                summary["files"] = data.get("files", {})
            else:
                # A passing pytest run is still useful when coverage cannot write its
                # report (for example, when this scanner is itself running under
                # coverage). Keep the pipeline moving with conservative AST candidates.
                files, parse_failures = _static_python_files(workspace, ignored)
                summary["files"] = files
                summary["baseline_mode"] = "coverage_fallback"
                summary["parse_failures"] = parse_failures
                summary["coverage_totals"] = {
                    "covered_lines": None,
                    "num_statements": sum(len(file_data["missing_lines"]) for file_data in files.values()),
                    "percent_covered": None,
                }
                baseline_status = "bootstrap" if files else "no_python_source"
                warning = (
                    "Tests passed, but coverage.py did not produce a JSON report; "
                    "continuing with AST-based candidates."
                    if files
                    else "Tests passed, but coverage.py did not produce a JSON report and no Python source files were found."
                )
        elif result.returncode == 5:
            files, parse_failures = _static_python_files(workspace, ignored)
            summary["files"] = files
            summary["baseline_mode"] = "bootstrap" if files else "no_python_source"
            summary["parse_failures"] = parse_failures
            summary["coverage_totals"] = {
                "covered_lines": 0,
                "num_statements": sum(len(file_data["missing_lines"]) for file_data in files.values()),
                "percent_covered": 0.0 if files else None,
            }
            if files:
                coverage_pct = 0.0
                baseline_status = "bootstrap"
                warning = (
                    "pytest found no tests; treating discovered Python statements as uncovered "
                    "and continuing in bootstrap mode."
                )
            else:
                baseline_status = "no_python_source"
                warning = "pytest found no tests and no testable Python source files were found."
        else:
            combined_output = summary["stdout"] + "\n" + summary["stderr"]
            if setup_warning or _is_environment_collection_failure(combined_output):
                files, parse_failures = _static_python_files(workspace, ignored)
                if files:
                    summary["files"] = files
                    summary["baseline_mode"] = "environment_bootstrap"
                    summary["parse_failures"] = parse_failures
                    summary["coverage_totals"] = {
                        "covered_lines": None,
                        "num_statements": sum(len(file_data["missing_lines"]) for file_data in files.values()),
                        "percent_covered": None,
                    }
                    baseline_status = "bootstrap"
                    warning = (
                        "Pytest collection could not start because project dependencies or required settings "
                        "are missing in the scanner environment. Coverage is unavailable; continuing with "
                        "AST-based candidates. Generated tests may remain unverified until setup is provided."
                    )
                    if setup_warning:
                        warning = f"{setup_warning} Coverage is unavailable; continuing with AST-based candidates."
                else:
                    baseline_status = "failed"
                    warning = (
                        "Pytest collection failed because project setup is missing, and no Python source "
                        "files were available for AST-based fallback."
                    )
            else:
                baseline_status = "failed"
                warning = "The existing baseline suite failed; generation is blocked until the baseline is understood."
        summary["baseline_status"] = baseline_status

    events = [
        {
            "type": "step.completed",
            "step": "baseline",
            "status": "success" if baseline_status == "passed" else "warning",
            "message": (
                f"Baseline passed; line coverage is {coverage_pct:.1f}%."
                if coverage_pct is not None and result.returncode == 0
                else warning or "Baseline command completed."
            ),
            "data": {"exit_code": result.returncode, "coverage_pct": coverage_pct},
        }
    ]
    return {
        "baseline_exit_code": result.returncode,
        "baseline_status": baseline_status,
        "baseline_summary": summary,
        "coverage_before_pct": coverage_pct,
        "warnings": [warning] if warning else [],
        "events": events,
    }

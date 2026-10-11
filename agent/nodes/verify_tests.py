"""Run drafted pytest candidates in a disposable copy and measure the result."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from agent.test_environment import (
    TestEnvironmentError,
    fallback_test_environment,
    prepare_test_environment,
)
from agent.state import TestGapState, report_progress
from agent.candidate_metrics import test_case_count

_IGNORED = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".aws", ".ssh", ".config", ".coverage",
}
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_MAX_DIAGNOSTIC_CHARS = 3000


def _verification_diagnostic(stdout_path: Path, stderr_path: Path, temp_root: Path) -> str | None:
    """Return a bounded, path-scrubbed pytest failure excerpt for the run record."""
    output = "\n".join(
        path.read_bytes()[-_MAX_DIAGNOSTIC_CHARS:].decode(errors="replace")
        for path in (stdout_path, stderr_path)
        if path.exists()
    ).strip()
    if not output:
        return None
    output = _ANSI_ESCAPE.sub("", output)
    output = output.replace(str(temp_root), "<temporary-run-dir>")
    if len(output) > _MAX_DIAGNOSTIC_CHARS:
        output = output[-_MAX_DIAGNOSTIC_CHARS:]
    return output


def _safe_test_path(value: str) -> Path:
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.suffix != ".py"
        or not relative.parts
    ):
        raise ValueError("Generated test path is not a safe relative Python path")
    return Path(*relative.parts)


def verify_tests(state: TestGapState) -> dict:
    candidates = state.get("generated_tests", [])
    if not candidates:
        return {"events": [{
            "type": "step.completed", "step": "verify_tests", "status": "skipped",
            "message": "No candidate tests were drafted, so test verification was skipped.",
            "data": {},
        }]}

    report_progress(
        state,
        step="verify_tests",
        message=f"Verifying {len(candidates)} generated test candidate(s) against the existing suite.",
        data={"candidate_count": len(candidates)},
    )
    root = Path(state["project_path"]).resolve(strict=True)
    timeout = state.get("run_timeout_seconds", 90)
    verified = []
    warnings = []
    events = []
    coverage_after_pct = None
    tests_added = 0
    baseline_environment = state.get("baseline_summary", {}).get("test_environment", {})

    for candidate in candidates:
        item = dict(candidate)
        diagnostic = None
        try:
            relative_test = _safe_test_path(item["test_path"])
            test_count = test_case_count(item["content"])
            if test_count == 0:
                raise ValueError("The draft contains no pytest test functions")

            with tempfile.TemporaryDirectory(prefix="testgap-verify-") as temp_dir:
                temp_root = Path(temp_dir)
                workspace = temp_root / root.name

                def ignore_entries(directory: str, names: list[str]) -> set[str]:
                    return {
                        name for name in names
                        if name in _IGNORED
                        or name == ".env"
                        or name.startswith(".env.")
                        or (Path(directory) / name).is_symlink()
                    }

                shutil.copytree(root, workspace, ignore=ignore_entries, symlinks=False)
                test_path = workspace / relative_test
                if test_path.exists():
                    raise ValueError("Generated test path already exists; existing tests were left untouched")
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(item["content"] + ("\n" if not item["content"].endswith("\n") else ""))

                coverage_file = temp_root / ".coverage"
                runner = Path(sys.executable)
                if state.get("repository_url"):
                    if baseline_environment.get("status") == "failed":
                        child_env = fallback_test_environment(root, temp_root)
                    else:
                        try:
                            runner, child_env, _ = prepare_test_environment(
                                root,
                                timeout_seconds=timeout,
                            )
                        except TestEnvironmentError:
                            child_env = fallback_test_environment(root, temp_root)
                    child_env["HOME"] = str(temp_root)
                    child_env["TMPDIR"] = str(temp_root)
                else:
                    child_env = {
                        "PATH": os.environ.get("PATH", ""),
                        "HOME": str(temp_root),
                        "TMPDIR": str(temp_root),
                        "PYTHONPATH": os.pathsep.join((str(workspace), str(workspace / "src"))),
                        "PYTHONDONTWRITEBYTECODE": "1",
                    }
                    if "SYSTEMROOT" in os.environ:
                        child_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
                child_env["PYTHONPATH"] = os.pathsep.join((str(workspace), str(workspace / "src")))
                child_env["COVERAGE_FILE"] = str(coverage_file)

                try:
                    stdout_path = temp_root / "pytest.stdout"
                    stderr_path = temp_root / "pytest.stderr"
                    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
                        result = subprocess.run(
                            [str(runner), "-m", "coverage", "run", "--branch", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=workspace,
                            stdout=stdout_file,
                            stderr=stderr_file,
                            timeout=timeout,
                            check=False,
                            shell=False,
                            env=child_env,
                        )
                    passed = result.returncode == 0
                    error = None if passed else f"pytest exited with code {result.returncode}"
                    diagnostic = None if passed else _verification_diagnostic(
                        stdout_path, stderr_path, temp_root
                    )
                    if diagnostic:
                        error = f"{error}. Pytest output:\n{diagnostic}"
                    if passed:
                        try:
                            report = subprocess.run(
                                [str(runner), "-m", "coverage", "json", "-o", str(temp_root / "coverage.json")],
                                cwd=workspace,
                                capture_output=True,
                                text=True,
                                timeout=timeout,
                                check=False,
                                shell=False,
                                env=child_env,
                            )
                            coverage_json = temp_root / "coverage.json"
                            if report.returncode == 0 and coverage_json.is_file():
                                coverage_data = json.loads(coverage_json.read_text())
                                coverage_after_pct = coverage_data.get("totals", {}).get("percent_covered")
                            else:
                                error = "Tests passed, but post-test coverage could not be measured"
                                passed = False
                        except subprocess.TimeoutExpired:
                            error = "Tests passed, but post-test coverage could not be measured"
                            passed = False
                except subprocess.TimeoutExpired:
                    passed = False
                    error = f"pytest exceeded the {timeout}-second verification limit"
                    diagnostic = _verification_diagnostic(stdout_path, stderr_path, temp_root)
                    if diagnostic:
                        error = f"{error}. Pytest output:\n{diagnostic}"

            item["test_count"] = test_count
            item["verification_status"] = "passed" if passed else "failed"
            item["verification_output"] = diagnostic if not passed else None
            item["verification_summary"] = (
                f"{test_count} generated test(s) passed with the repository suite."
                if passed else f"Generated tests were not accepted: {error}."
            )
            verified.append(item)
            if passed:
                tests_added += test_count
                events.append({
                    "type": "step.completed", "step": "verify_tests", "status": "success",
                    "message": item["verification_summary"],
                    "data": {"test_count": test_count, "coverage_after_pct": coverage_after_pct},
                })
            else:
                warnings.append(item["verification_summary"])
                events.append({
                    "type": "step.completed", "step": "verify_tests", "status": "warning",
                    "message": item["verification_summary"],
                    "data": {"test_count": test_count, "pytest_output": diagnostic},
                })
        except (KeyError, OSError, SyntaxError, ValueError) as exc:
            item["verification_status"] = "failed"
            item["test_count"] = 0
            item["verification_summary"] = f"Generated test rejected: {exc}"
            verified.append(item)
            warnings.append(item["verification_summary"])
            events.append({
                "type": "step.completed", "step": "verify_tests", "status": "warning",
                "message": item["verification_summary"], "data": {},
            })

    return {
        "generated_tests": verified,
        "coverage_after_pct": coverage_after_pct,
        "tests_added": tests_added,
        "warnings": warnings,
        "events": events,
    }

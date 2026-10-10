"""Run drafted pytest candidates in a disposable copy and measure the result."""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from agent.state import TestGapState

_IGNORED = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".aws", ".ssh", ".config", ".coverage",
}


def _test_case_count(source: str) -> int:
    tree = ast.parse(source)
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


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

    root = Path(state["project_path"]).resolve(strict=True)
    timeout = state.get("run_timeout_seconds", 90)
    verified = []
    warnings = []
    events = [{
        "type": "step.started", "step": "verify_tests", "status": "running",
        "message": "Running drafted tests in a disposable repository copy.", "data": {},
    }]
    coverage_after_pct = None
    tests_added = 0

    for candidate in candidates:
        item = dict(candidate)
        try:
            relative_test = _safe_test_path(item["test_path"])
            test_count = _test_case_count(item["content"])
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
                child_env = {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": str(temp_root),
                    "TMPDIR": str(temp_root),
                    "PYTHONPATH": os.pathsep.join((str(workspace), str(workspace / "src"))),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "COVERAGE_FILE": str(coverage_file),
                }
                if "SYSTEMROOT" in os.environ:
                    child_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]

                try:
                    stdout_path = temp_root / "pytest.stdout"
                    stderr_path = temp_root / "pytest.stderr"
                    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
                        result = subprocess.run(
                            [sys.executable, "-m", "coverage", "run", "--branch", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
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
                    if passed:
                        try:
                            report = subprocess.run(
                                [sys.executable, "-m", "coverage", "json", "-o", str(temp_root / "coverage.json")],
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

            item["test_count"] = test_count
            item["verification_status"] = "passed" if passed else "failed"
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
                    "message": item["verification_summary"], "data": {"test_count": test_count},
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

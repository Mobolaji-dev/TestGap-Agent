"""Run drafted pytest candidates in a disposable copy, repairing failures within budget."""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from time import perf_counter

from agent.candidate_metrics import test_case_count
from agent.state import TestGapState, report_progress
from agent.test_environment import (
    TestEnvironmentError,
    fallback_test_environment,
    prepare_test_environment,
)
from app.config.settings import settings
from agent.telemetry import wrap_llm_client
from openai import OpenAI

logger = logging.getLogger(__name__)

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
    output = _ANSI_ESCAPE.sub("", output).replace(str(temp_root), "<temporary-run-dir>")
    return output[-_MAX_DIAGNOSTIC_CHARS:]


def _safe_test_path(value: str) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".py" or not relative.parts:
        raise ValueError("Generated test path is not a safe relative Python path")
    return Path(*relative.parts)


def _run_candidate(
    root: Path,
    item: dict,
    *,
    timeout: int,
    baseline_environment: dict,
) -> tuple[bool, str | None, str | None, float | None]:
    """Execute one candidate with the repo's suite in a disposable copy."""
    relative_test = _safe_test_path(item["test_path"])
    if test_case_count(item["content"]) == 0:
        raise ValueError("The draft contains no pytest test functions")

    with tempfile.TemporaryDirectory(prefix="testgap-verify-") as temp_dir:
        temp_root = Path(temp_dir)
        workspace = temp_root / root.name

        def ignore_entries(directory: str, names: list[str]) -> set[str]:
            return {
                name for name in names
                if name in _IGNORED or name == ".env" or name.startswith(".env.")
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
        if baseline_environment.get("status") == "failed":
            child_env = fallback_test_environment(root, temp_root)
        else:
            try:
                runner, child_env, _ = prepare_test_environment(root, timeout_seconds=timeout)
            except TestEnvironmentError:
                child_env = fallback_test_environment(root, temp_root)
        child_env["HOME"] = str(temp_root)
        child_env["TMPDIR"] = str(temp_root)
        child_env["PYTHONPATH"] = os.pathsep.join((str(workspace), str(workspace / "src")))
        child_env["COVERAGE_FILE"] = str(coverage_file)
        if "SYSTEMROOT" in os.environ:
            child_env.setdefault("SYSTEMROOT", os.environ["SYSTEMROOT"])

        stdout_path = temp_root / "pytest.stdout"
        stderr_path = temp_root / "pytest.stderr"
        try:
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
        except subprocess.TimeoutExpired:
            diagnostic = _verification_diagnostic(stdout_path, stderr_path, temp_root)
            return False, f"pytest exceeded the {timeout}-second verification limit", diagnostic, None

        diagnostic = None if result.returncode == 0 else _verification_diagnostic(
            stdout_path, stderr_path, temp_root
        )
        if result.returncode != 0:
            message = f"pytest exited with code {result.returncode}"
            if diagnostic:
                message = f"{message}. Pytest output:\n{diagnostic}"
            return False, message, diagnostic, None

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
                coverage_pct = json.loads(coverage_json.read_text()).get("totals", {}).get("percent_covered")
                return True, None, None, coverage_pct
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
        return False, "Tests passed, but post-test coverage could not be measured", None, None


def _repair_candidate(state: TestGapState, item: dict, diagnostic: str, attempt: int) -> dict | None:
    """Ask the configured model to repair a failed candidate using actual pytest output."""
    if not settings.litellm_api_key:
        return None
    try:
        project_root = Path(state["project_path"]).resolve(strict=True)
        target_path = (project_root / Path(item["target_path"])).resolve(strict=True)
        target_path.relative_to(project_root)
        target_source = target_path.read_text(errors="replace")[:12_000]
        client = OpenAI(
            api_key=settings.litellm_api_key.get_secret_value(),
            base_url=settings.litellm_base_url,
            timeout=45,
            max_retries=1,
        )
        client = wrap_llm_client(
            client,
            run_id=state.get("run_id"),
            project_id=state.get("project_id"),
            target=item.get("target_path"),
        )
        started = perf_counter()
        response = client.chat.completions.create(
            model=settings.litellm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are repairing a pytest module that failed in the target repository. "
                        "Use only the supplied test code and real pytest output. Return a complete "
                        "corrected pytest file only. Do not change application code or invent routes/imports."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Target: {item.get('target_path')}\nTest file: {item.get('test_path')}\n\n"
                        f"Actual target source:\n```python\n{target_source}\n```\n\n"
                        f"Current candidate:\n```python\n{item['content']}\n```\n\n"
                        f"Actual pytest failure output:\n```text\n{diagnostic[-_MAX_DIAGNOSTIC_CHARS:]}\n```\n\n"
                        "Fix the candidate to test behavior that the target source actually implements. "
                        "Do not weaken assertions just to hide failures. Preserve useful test intent, "
                        "remove or rewrite cases whose assumptions are wrong, and return syntactically complete code."
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=2_000,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3].strip()
        count = test_case_count(content)
        if not content or count == 0 or len(content.splitlines()) > 100:
            return None
        usage = getattr(response, "usage", None)
        return {
            **item,
            "content": content,
            "test_count": count,
            "finish_reason": getattr(choice, "finish_reason", None),
            "repair_attempts": attempt,
            "repair_usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "duration_ms": int((perf_counter() - started) * 1000),
            },
        }
    except Exception as exc:
        logger.warning("Candidate test repair failed (%s)", type(exc).__name__)
        return None


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
    repair_limit = max(0, min(int(state.get("repair_limit", 0)), 2))
    baseline_environment = state.get("baseline_summary", {}).get("test_environment", {})
    verified = []
    warnings = []
    events = []
    coverage_after_pct = None
    tests_added = 0

    for original in candidates:
        item = dict(original)
        diagnostic = None
        error = None
        passed = False
        test_count = 0
        repair_attempts = 0
        try:
            _safe_test_path(item["test_path"])
            for attempt in range(repair_limit + 1):
                repair_attempts = attempt
                test_count = test_case_count(item["content"])
                if test_count == 0:
                    raise ValueError("The draft contains no pytest test functions")
                passed, error, diagnostic, measured_coverage = _run_candidate(
                    root,
                    item,
                    timeout=timeout,
                    baseline_environment=baseline_environment,
                )
                if passed:
                    coverage_after_pct = measured_coverage
                    break
                if attempt >= repair_limit or not diagnostic:
                    break
                report_progress(
                    state,
                    step="verify_tests",
                    event_type="step.progress",
                    message=f"Repairing failed test candidate (attempt {attempt + 1} of {repair_limit}).",
                    data={"target_path": item.get("target_path"), "repair_attempt": attempt + 1},
                )
                repaired = _repair_candidate(state, item, diagnostic, attempt + 1)
                if repaired is None:
                    break
                item = repaired

            item["test_count"] = test_count
            item["repair_attempts"] = repair_attempts
            item["verification_status"] = "passed" if passed else "failed"
            item["verification_output"] = diagnostic if not passed else None
            if passed:
                tests_added += test_count
                item["verification_summary"] = (
                    f"{test_count} generated test(s) passed with the repository suite."
                    if repair_attempts == 0
                    else f"{test_count} generated test(s) passed after {repair_attempts} model repair attempt(s)."
                )
                events.append({
                    "type": "step.completed", "step": "verify_tests", "status": "success",
                    "message": item["verification_summary"],
                    "data": {
                        "test_count": test_count,
                        "repair_attempts": repair_attempts,
                        "coverage_after_pct": coverage_after_pct,
                    },
                })
            else:
                item["verification_summary"] = f"Generated tests were not accepted: {error}."
                warnings.append(item["verification_summary"])
                events.append({
                    "type": "step.completed", "step": "verify_tests", "status": "warning",
                    "message": item["verification_summary"],
                    "data": {"test_count": test_count, "repair_attempts": repair_attempts, "pytest_output": diagnostic},
                })
            verified.append(item)
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

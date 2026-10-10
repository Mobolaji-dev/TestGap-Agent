import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from agent.state import TestGapState


def run_baseline(state: TestGapState) -> dict:
    root = Path(state["project_path"]).resolve(strict=True)
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
        child_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": temp_dir,
            "PYTHONPATH": str(workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if "SYSTEMROOT" in os.environ:
            child_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            result = subprocess.run(
                [
                    sys.executable, "-m", "coverage", "run", "--branch", "-m", "pytest",
                    "-q", "-p", "no:cacheprovider",
                ],
                cwd=workspace,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=state.get("run_timeout_seconds", 90),
                check=False,
                shell=False,
                env=child_env,
            )
        summary: dict = {
            **state.get("baseline_summary", {}),
            "command": "python -m coverage run --branch -m pytest -q",
            "exit_code": result.returncode,
            "stdout": stdout_path.read_bytes()[-8000:].decode(errors="replace"),
            "stderr": stderr_path.read_bytes()[-8000:].decode(errors="replace"),
        }
        warning = None
        coverage_pct = None
        if result.returncode == 0:
            report = subprocess.run(
                [sys.executable, "-m", "coverage", "json", "-o", str(coverage_file)],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=state.get("run_timeout_seconds", 90),
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
                warning = "Tests passed, but coverage.py did not produce a JSON report."
        elif result.returncode == 5:
            warning = "pytest found no tests in this project."
        else:
            warning = "The existing baseline suite failed; generation is blocked until the baseline is understood."

    events = [
        {
            "type": "step.completed",
            "step": "baseline",
            "status": "success" if result.returncode == 0 else "warning",
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
        "baseline_summary": summary,
        "coverage_before_pct": coverage_pct,
        "warnings": [warning] if warning else [],
        "events": events,
    }

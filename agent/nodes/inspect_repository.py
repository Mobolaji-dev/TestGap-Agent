from pathlib import Path

from agent.state import TestGapState


def inspect_repository(state: TestGapState) -> dict:
    root = Path(state["project_path"]).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Configured project path is not a directory")

    config_files = [name for name in ("pyproject.toml", "pytest.ini", "setup.cfg") if (root / name).exists()]
    test_dirs = [name for name in ("tests", "test") if (root / name).is_dir()]
    return {
        "baseline_summary": {
            "project_name": root.name,
            "config_files": config_files,
            "test_directories": test_dirs,
        },
        "events": [
            {
                "type": "step.completed",
                "step": "inspection",
                "status": "success",
                "message": f"Inspected {root.name}; found {len(test_dirs)} test directories.",
                "data": {"config_files": config_files, "test_directories": test_dirs},
            }
        ],
    }

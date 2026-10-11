import logging
from pathlib import Path
from time import perf_counter

from openai import OpenAI

from agent.prompts.test_writer import build_test_writer_prompt, TEST_WRITER_SYSTEM_PROMPT
from agent.state import TestGapState
from agent.candidate_metrics import test_case_count
from agent.telemetry import wrap_llm_client
from app.config.settings import settings

logger = logging.getLogger(__name__)
_MAX_SOURCE_CHARS = 12_000


def _target_file(root: Path, value: str) -> tuple[Path, str]:
    raw = Path(value)
    if raw.is_absolute():
        try:
            relative = raw.relative_to(root)
        except ValueError:
            # Coverage JSON may identify the temporary baseline copy; map its
            # project-name suffix back into the configured source checkout.
            parts = raw.parts
            matches = [index for index, part in enumerate(parts[:-1]) if part == root.name]
            if not matches:
                raise ValueError("Coverage target is outside the configured project")
            relative = Path(*parts[matches[-1] + 1 :])
    else:
        relative = raw

    source = (root / relative).resolve(strict=True)
    source.relative_to(root)
    if not source.is_file() or source.suffix != ".py":
        raise ValueError("Ranked target is not a Python source file")
    return source, relative.as_posix()


def _source_excerpt(source: str, uncovered_lines: list[int]) -> str:
    lines = source.splitlines()
    selected: set[int] = set()
    for line_number in uncovered_lines:
        selected.update(range(max(1, line_number - 4), min(len(lines), line_number + 4) + 1))
    if not selected:
        selected.update(range(1, min(len(lines), 120) + 1))
    excerpt = "\n".join(f"{number}: {lines[number - 1]}" for number in sorted(selected))
    return excerpt[:_MAX_SOURCE_CHARS]


def _read_small_file(path: Path, limit: int) -> str:
    try:
        return path.read_text(errors="replace")[:limit]
    except OSError:
        return ""


def _candidate_test_path(root: Path, source_path: Path) -> str:
    test_dir = next(
        (name for name in ("tests", "test") if (root / name).is_dir()),
        "tests",
    )
    stem = f"test_{source_path.stem}_testgap"
    candidate = Path(test_dir) / f"{stem}.py"
    suffix = 2
    while (root / candidate).exists():
        candidate = Path(test_dir) / f"{stem}_{suffix}.py"
        suffix += 1
    return candidate.as_posix()


def write_tests(state: TestGapState) -> dict:
    targets = state.get("targets", [])
    if not targets:
        return {
            "generated_tests": [],
            "warnings": ["No ranked Python gap was available for test drafting."],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "skipped",
                "message": "No ranked gap was available for test drafting.", "data": {},
            }],
        }

    if not settings.litellm_api_key:
        message = "Test drafting is not configured; set LITELLM_API_KEY in the backend environment."
        return {
            "generated_tests": [],
            "warnings": [message],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "skipped",
                "message": message, "data": {},
            }],
        }

    root = Path(state["project_path"]).resolve(strict=True)
    target = targets[0]  # One model call per run keeps the shared hackathon budget bounded.
    try:
        source_path, relative_path = _target_file(root, target["path"])
        source_text = _read_small_file(source_path, 100_000)
        excerpt = _source_excerpt(source_text, target.get("uncovered_lines", []))
        readme = _read_small_file(root / "README.md", 5_000)
        prompt = build_test_writer_prompt(
            target_path=relative_path,
            source=excerpt,
            uncovered_lines=target.get("uncovered_lines", []),
            project_rules=readme,
        )
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
            target=relative_path,
        )
        started = perf_counter()
        response = client.chat.completions.create(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": TEST_WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2_000,
        )
        duration_ms = int((perf_counter() - started) * 1000)
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3].strip()
        if not content:
            raise ValueError("The model returned an empty test draft")
        drafted_test_count = test_case_count(content)
        if drafted_test_count == 0:
            raise ValueError("The model returned no pytest test functions")

        usage = response.usage
        usage_data = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "duration_ms": duration_ms,
        }
        candidate = {
            "target_path": relative_path,
            "test_path": _candidate_test_path(root, source_path),
            "content": content,
            "model": settings.litellm_model,
            "test_count": drafted_test_count,
        }
        return {
            "generated_tests": [candidate],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "success",
                "message": f"Drafted a candidate test for {relative_path}.",
                "data": {"model": settings.litellm_model, "test_count": drafted_test_count, **usage_data},
            }],
        }
    except Exception as exc:
        logger.warning("Test drafting failed (%s)", type(exc).__name__)
        message = f"Test drafting failed ({type(exc).__name__}); baseline coverage and ranked gaps are still available."
        return {
            "generated_tests": [],
            "warnings": [message],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "warning",
                "message": message,
                "data": {"model": settings.litellm_model},
            }],
        }

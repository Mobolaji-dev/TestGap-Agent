import logging
import ast
from pathlib import Path
from time import perf_counter

from openai import OpenAI

from agent.prompts.test_writer import build_test_writer_prompt, TEST_WRITER_SYSTEM_PROMPT
from agent.state import TestGapState, report_progress
from agent.candidate_metrics import (
    DraftValidationError,
    extract_code_block,
    normalize_test_draft,
    test_case_count,
    validate_test_draft,
)
from agent.telemetry import wrap_llm_client
from app.config.settings import settings

logger = logging.getLogger(__name__)
_MAX_SOURCE_CHARS = 12_000
_MAX_FOCUS_LINES = 12
_MAX_GENERATED_TESTS = 12
_MAX_GENERATED_LINES = 250

_validate_test_draft = validate_test_draft
_normalize_test_draft = normalize_test_draft


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
    try:
        module = ast.parse(source)
    except SyntaxError:
        module = None
    if module is not None:
        # Give the model the real import paths even when the measured gap is
        # far below the import block; this prevents guessed project modules.
        for node in module.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                selected.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
            # Router prefixes define the externally visible path. Keep them in
            # context even when coverage points only at the endpoint body.
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if isinstance(value, ast.Call) and getattr(value.func, "id", None) == "APIRouter":
                    selected.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
            # Include all route decorators so the model can see exact sibling
            # endpoint patterns without receiving the entire module.
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in child.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in {"get", "post", "put", "patch", "delete", "options", "head"}:
                                selected.update(range(decorator.lineno, (decorator.end_lineno or decorator.lineno) + 1))
    for line_number in uncovered_lines:
        selected.update(range(max(1, line_number - 4), min(len(lines), line_number + 4) + 1))
    if not selected:
        selected.update(range(1, min(len(lines), 120) + 1))
    excerpt = "\n".join(f"{number}: {lines[number - 1]}" for number in sorted(selected))
    return excerpt[:_MAX_SOURCE_CHARS]


def _known_routes(source: str) -> list[str]:
    """Resolve literal FastAPI APIRouter prefixes and route decorators."""
    try:
        module = ast.parse(source)
    except SyntaxError:
        return []

    prefixes: dict[str, str] = {}
    routes: list[str] = []
    for node in module.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Call):
            if getattr(node.value.func, "id", None) == "APIRouter":
                prefix = ""
                for keyword in node.value.keywords:
                    if keyword.arg == "prefix":
                        try:
                            prefix = ast.literal_eval(keyword.value)
                        except (ValueError, TypeError):
                            prefix = ""
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        prefixes[target.id] = prefix if isinstance(prefix, str) else ""

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            router = decorator.func.value
            if not isinstance(router, ast.Name) or router.id not in prefixes:
                continue
            try:
                child_path = ast.literal_eval(decorator.args[0]) if decorator.args else ""
            except (ValueError, TypeError):
                continue
            if not isinstance(child_path, str):
                continue
            path = f"{prefixes[router.id].rstrip('/')}/{child_path.lstrip('/')}"
            routes.append(f"{decorator.func.attr.upper()} {path or '/'}")
    return routes


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
        report_progress(
            state,
            step="write_tests",
            message=f"Preparing a model request to draft tests for {relative_path}.",
            data={"model": settings.litellm_model, "target_path": relative_path},
        )
        source_text = _read_small_file(source_path, 100_000)
        focus_lines = target.get("uncovered_lines", [])[:_MAX_FOCUS_LINES]
        excerpt = _source_excerpt(source_text, focus_lines)
        readme = _read_small_file(root / "README.md", 5_000)
        prompt = build_test_writer_prompt(
            target_path=relative_path,
            source=excerpt,
            uncovered_lines=focus_lines,
            project_rules=readme,
            route_context="\n".join(_known_routes(source_text)),
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
        report_progress(
            state,
            step="write_tests",
            event_type="step.progress",
            message=f"Calling {settings.litellm_model} to draft tests for {relative_path}.",
            data={"model": settings.litellm_model, "target_path": relative_path},
        )
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
        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        content = extract_code_block(choice.message.content or "")
        if not content:
            raise ValueError("The model returned an empty test draft")
        content, salvaged = _normalize_test_draft(content)
        drafted_test_count = _validate_test_draft(content)

        usage = response.usage
        usage_data = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "duration_ms": duration_ms,
            "finish_reason": finish_reason,
        }
        candidate = {
            "target_path": relative_path,
            "test_path": _candidate_test_path(root, source_path),
            "content": content,
            "model": settings.litellm_model,
            "test_count": drafted_test_count,
            "finish_reason": finish_reason,
        }
        return {
            "generated_tests": [candidate],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "success",
                "message": (
                    f"Kept {drafted_test_count} complete test(s) from a truncated model draft for {relative_path}."
                    if salvaged else f"Drafted {drafted_test_count} candidate test(s) for {relative_path}."
                ),
                "data": {
                    "model": settings.litellm_model,
                    "test_count": drafted_test_count,
                    "truncated_output_salvaged": salvaged,
                    **usage_data,
                },
            }],
        }
    except DraftValidationError as exc:
        message = f"Model draft rejected: {exc}. No candidate tests were saved."
        logger.warning("%s", message)
        return {
            "generated_tests": [],
            "warnings": [message],
            "events": [{
                "type": "step.completed", "step": "write_tests", "status": "warning",
                "message": message,
                "data": {"model": settings.litellm_model, "validation_error": str(exc)},
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

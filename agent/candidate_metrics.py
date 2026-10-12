"""Small helpers for accurately reporting and normalizing drafted pytest functions."""

import ast
import re

_MAX_GENERATED_TESTS = 12
_MAX_GENERATED_LINES = 250


class DraftValidationError(ValueError):
    """A safe, user-facing reason a model draft was rejected before verification."""


def test_case_count(source: str) -> int:
    """Count top-level and nested pytest test functions in candidate source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def extract_code_block(content: str) -> str:
    """Extract Python code from model response, handling fences and conversational wrappers."""
    text = content.strip()
    # Look for code blocks with python or generic fences
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if blocks:
        for block in reversed(blocks):
            if "def test_" in block or "async def test_" in block:
                return block.strip()
        return blocks[0].strip()

    # If starts with ``` but closing ``` is missing (e.g. truncated)
    if text.startswith("```"):
        lines = text.splitlines()
        code_lines = lines[1:]
        if code_lines and code_lines[-1].strip() == "```":
            code_lines = code_lines[:-1]
        return "\n".join(code_lines).strip()

    # If opening fence appears in conversational text without closing fence
    trunc_match = re.search(r"```(?:python|py)?\s*\n(.*)", text, re.DOTALL | re.IGNORECASE)
    if trunc_match and ("def test_" in trunc_match.group(1) or "async def test_" in trunc_match.group(1)):
        return trunc_match.group(1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def validate_test_draft(
    content: str,
    *,
    max_tests: int = _MAX_GENERATED_TESTS,
    max_lines: int = _MAX_GENERATED_LINES,
) -> int:
    """Validate that candidate source is valid Python containing acceptable pytest functions."""
    try:
        ast.parse(content)
    except SyntaxError:
        raise DraftValidationError("the model returned incomplete or invalid Python") from None
    count = test_case_count(content)
    if count == 0:
        raise DraftValidationError("the draft contains no pytest test functions")
    if count > max_tests:
        raise DraftValidationError(
            f"the draft contains {count} test functions; the limit is {max_tests}"
        )
    lines = len(content.splitlines())
    if lines > max_lines:
        raise DraftValidationError(
            f"the draft contains {lines} lines; the limit is {max_lines}"
        )
    return count


def normalize_test_draft(content: str) -> tuple[str, bool]:
    """Keep complete test functions when the provider truncates its final draft."""
    try:
        ast.parse(content)
        return content, False
    except SyntaxError:
        lines = content.splitlines()
        test_starts = [
            index for index, line in enumerate(lines)
            if line.startswith("def test_") or line.startswith("async def test_")
        ]
        best_prefix = ""
        for boundary in test_starts[1:]:
            prefix = "\n".join(lines[:boundary]).rstrip()
            try:
                ast.parse(prefix)
            except SyntaxError:
                continue
            if test_case_count(prefix) > 0 and len(prefix) > len(best_prefix):
                best_prefix = prefix
        if best_prefix:
            return best_prefix, True
        raise DraftValidationError("the model returned incomplete or invalid Python") from None


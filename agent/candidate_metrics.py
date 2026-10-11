"""Small helpers for accurately reporting drafted pytest functions."""

import ast


def test_case_count(source: str) -> int:
    """Count top-level and nested pytest test functions in candidate source."""
    tree = ast.parse(source)
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )

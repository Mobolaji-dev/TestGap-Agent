import pytest

from agent.nodes.write_tests import (
    DraftValidationError,
    _normalize_test_draft,
    _source_excerpt,
    _validate_test_draft,
)


def test_source_excerpt_keeps_target_imports_for_distant_coverage_gaps():
    source = (
        "from app.services.auth_service import AuthService\n"
        "from app.services.supabase_auth import SupabaseAuthError\n"
        "\n"
        "def helper():\n"
        "    return None\n"
        "\n"
        "\n"
        "\n"
        "def uncovered():\n"
        "    return AuthService, SupabaseAuthError\n"
    )

    excerpt = _source_excerpt(source, [10])

    assert "from app.services.auth_service import AuthService" in excerpt
    assert "from app.services.supabase_auth import SupabaseAuthError" in excerpt
    assert "def uncovered():" in excerpt


def test_validation_accepts_a_complete_bounded_draft_with_more_than_three_tests():
    content = "\n\n".join(
        f"def test_case_{index}():\n    assert {index} == {index}"
        for index in range(1, 10)
    )

    assert _validate_test_draft(content) == 9


def test_validation_reports_invalid_python_as_a_safe_reason():
    with pytest.raises(DraftValidationError, match="incomplete or invalid Python"):
        _validate_test_draft("def test_incomplete():\n    assert True\n    if")


def test_normalizer_keeps_complete_tests_before_a_truncated_function():
    content = (
        "def test_one():\n    assert 1 == 1\n\n"
        "def test_two():\n    assert 2 == 2\n\n"
        "def test_truncated():\n    assert 3 == 3\n    if"
    )

    normalized, salvaged = _normalize_test_draft(content)

    assert salvaged is True
    assert _validate_test_draft(normalized) == 2
    assert "def test_truncated" not in normalized

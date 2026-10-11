from agent.nodes.write_tests import _source_excerpt


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

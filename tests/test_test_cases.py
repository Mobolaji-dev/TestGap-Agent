from agent.candidate_metrics import test_case_count as count_tests


def test_test_case_count_counts_sync_and_async_pytest_functions():
    source = (
        "def test_sync():\n    pass\n\n"
        "async def test_async():\n    pass\n\n"
        "def helper():\n    pass\n"
    )

    assert count_tests(source) == 2


def test_test_case_count_returns_zero_when_draft_has_no_tests():
    assert count_tests("def helper():\n    return True\n") == 0

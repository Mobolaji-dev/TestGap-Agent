from agent.candidate_metrics import (
    extract_code_block,
    test_case_count as count_tests,
)


def test_test_case_count_counts_sync_and_async_pytest_functions():
    source = (
        "def test_sync():\n    pass\n\n"
        "async def test_async():\n    pass\n\n"
        "def helper():\n    pass\n"
    )

    assert count_tests(source) == 2


def test_test_case_count_returns_zero_when_draft_has_no_tests():
    assert count_tests("def helper():\n    return True\n") == 0


def test_test_case_count_returns_zero_on_invalid_syntax():
    assert count_tests("def test_broken(:\n    assert True") == 0


def test_extract_code_block_extracts_from_fenced_markdown():
    wrapped = "Here is the test:\n```python\ndef test_one():\n    assert 1 == 1\n```\nHope this helps!"
    extracted = extract_code_block(wrapped)
    assert extracted == "def test_one():\n    assert 1 == 1"


def test_extract_code_block_handles_unclosed_fence():
    truncated = "```python\ndef test_one():\n    assert 1 == 1\ndef test_two():\n    assert 2 =="
    extracted = extract_code_block(truncated)
    assert extracted == "def test_one():\n    assert 1 == 1\ndef test_two():\n    assert 2 =="


def test_extract_code_block_handles_bare_code():
    code = "def test_bare():\n    assert True"
    assert extract_code_block(code) == code


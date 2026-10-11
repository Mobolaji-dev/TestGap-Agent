from agent.nodes.rank_gaps import rank_gaps


def test_ast_fallback_labels_candidates_as_estimates():
    result = rank_gaps(
        {
            "baseline_status": "bootstrap",
            "baseline_summary": {
                "files": {
                    "app/api/auth.py": {
                        "executed_lines": [],
                        "missing_lines": [10, 11],
                        "missing_branches": [],
                    }
                }
            },
        }
    )

    target = result["targets"][0]
    assert target["coverage_basis"] == "ast_estimate"
    assert "not confirmed uncovered" in target["rationale"][1]
    assert "AST candidate" in result["events"][0]["message"]


def test_coverage_results_remain_measured_targets():
    result = rank_gaps(
        {
            "baseline_status": "passed",
            "baseline_summary": {
                "files": {
                    "app.py": {
                        "executed_lines": [1],
                        "missing_lines": [2],
                        "missing_branches": [],
                    }
                }
            },
        }
    )

    assert result["targets"][0]["coverage_basis"] == "measured_coverage"
    assert "1 executable lines are uncovered." in result["targets"][0]["rationale"][0]

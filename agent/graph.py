import logging

from langgraph.graph import END, START, StateGraph

from agent.nodes.inspect_repository import inspect_repository
from agent.nodes.rank_gaps import rank_gaps
from agent.nodes.run_baseline import run_baseline
from agent.nodes.write_tests import write_tests
from agent.nodes.verify_tests import verify_tests
from agent.state import TestGapState

logger = logging.getLogger(__name__)


def route_after_baseline(state: TestGapState) -> str:
    return "rank_gaps" if state.get("baseline_status") in {"passed", "bootstrap", "no_python_source"} else END


def build_graph():
    builder = StateGraph(TestGapState)
    builder.add_node("inspect_repository", inspect_repository)
    builder.add_node("run_baseline", run_baseline)
    builder.add_node("rank_gaps", rank_gaps)
    builder.add_node("write_tests", write_tests)
    builder.add_node("verify_tests", verify_tests)
    builder.add_edge(START, "inspect_repository")
    builder.add_edge("inspect_repository", "run_baseline")
    builder.add_conditional_edges(
        "run_baseline",
        route_after_baseline,
        {"rank_gaps": "rank_gaps", END: END},
    )
    builder.add_edge("rank_gaps", "write_tests")
    builder.add_edge("write_tests", "verify_tests")
    builder.add_edge("verify_tests", END)
    graph = builder.compile()
    logger.info("TestGap Finder LangGraph workflow compiled")
    return graph

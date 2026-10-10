import logging

from langgraph.graph import END, START, StateGraph

from agent.nodes.inspect_repository import inspect_repository
from agent.nodes.rank_gaps import rank_gaps
from agent.nodes.run_baseline import run_baseline
from agent.state import TestGapState

logger = logging.getLogger(__name__)


def route_after_baseline(state: TestGapState) -> str:
    return "rank_gaps" if state.get("baseline_exit_code") == 0 else END


def build_graph():
    builder = StateGraph(TestGapState)
    builder.add_node("inspect_repository", inspect_repository)
    builder.add_node("run_baseline", run_baseline)
    builder.add_node("rank_gaps", rank_gaps)
    builder.add_edge(START, "inspect_repository")
    builder.add_edge("inspect_repository", "run_baseline")
    builder.add_conditional_edges(
        "run_baseline",
        route_after_baseline,
        {"rank_gaps": "rank_gaps", END: END},
    )
    builder.add_edge("rank_gaps", END)
    graph = builder.compile()
    logger.info("TestGap Finder LangGraph workflow compiled")
    return graph

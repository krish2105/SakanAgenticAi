"""LangGraph wiring for the 5-agent pipeline (ARCHITECTURE.md Section 5.7)."""
from __future__ import annotations

from typing import Callable

from langgraph.graph import END, StateGraph

from app.agents.comps_agent import comps_agent_node
from app.agents.compliance_agent import compliance_agent_node
from app.agents.memo_agent import memo_agent_node
from app.agents.query_agent import query_agent_node
from app.agents.valuation_agent import valuation_agent_node
from app.deal_state import DealState


def _as_graph_node(fn: Callable[[DealState], DealState]):
    """LangGraph node functions return a dict of state updates; our agent
    functions are easier to unit test as DealState -> DealState, so this
    adapts one to the other without changing the agent signatures."""

    def node(state: DealState) -> dict:
        updated = fn(state)
        return updated.model_dump()

    node.__name__ = fn.__name__
    return node


def _route_after_comps(state: DealState) -> str:
    """Stretch goal from ARCHITECTURE.md Section 5.7: a comps_search query
    doesn't need valuation/compliance/memo, so skip straight to END after
    comps instead of running the full pipeline -- cheaper and faster for
    simple lookups."""
    return "end" if state.query_type == "comps_search" else "continue"


def build_graph():
    graph = StateGraph(DealState)

    graph.add_node("query", _as_graph_node(query_agent_node))
    graph.add_node("comps", _as_graph_node(comps_agent_node))
    graph.add_node("valuation", _as_graph_node(valuation_agent_node))
    graph.add_node("compliance", _as_graph_node(compliance_agent_node))
    graph.add_node("memo", _as_graph_node(memo_agent_node))

    graph.set_entry_point("query")
    graph.add_edge("query", "comps")
    graph.add_conditional_edges("comps", _route_after_comps, {"end": END, "continue": "valuation"})
    graph.add_edge("valuation", "compliance")
    graph.add_edge("compliance", "memo")
    graph.add_edge("memo", END)

    return graph.compile()


deal_pipeline = None  # lazily built via get_deal_pipeline() to avoid import-time DB/Qdrant setup


def get_deal_pipeline():
    global deal_pipeline
    if deal_pipeline is None:
        deal_pipeline = build_graph()
    return deal_pipeline

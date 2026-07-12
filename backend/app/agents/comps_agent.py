"""Agent 2 — Comps Agent (ARCHITECTURE.md Section 5.3)."""
from __future__ import annotations

from app.db import get_session_factory
from app.deal_state import DealState
from app.services.comps_service import query_transactions_sql, semantic_rerank


def comps_agent_node(state: DealState) -> DealState:
    state.trace("comps", "running")
    try:
        session_factory = get_session_factory()
        with session_factory() as session:
            sql_comps = query_transactions_sql(
                session,
                community=state.community,
                property_type=state.property_type,
                bedrooms=state.bedrooms,
                budget_range=(state.budget_min, state.budget_max),
                limit=25,
            )
        reranked = semantic_rerank(sql_comps, query=state.raw_query, top_k=8)
        state.retrieved_comps = reranked
        state.trace("comps", "done", count=len(reranked))
    except Exception as exc:  # noqa: BLE001
        # Every other node in this pipeline degrades to a fallback on
        # failure instead of aborting the run (see valuation_agent's
        # _fallback_valuation, compliance_agent's "unable to verify").
        # This one didn't, so a transient DB hiccup here used to take the
        # whole deal query down with it instead of just leaving comps
        # empty -- downstream agents already handle that (Valuation Agent
        # already falls back on an empty retrieved_comps).
        state.retrieved_comps = []
        state.trace("comps", "error", detail=str(exc))
    return state

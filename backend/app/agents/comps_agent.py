"""Agent 2 — Comps Agent (ARCHITECTURE.md Section 5.3)."""
from __future__ import annotations

from app.db import get_session_factory
from app.deal_state import DealState
from app.services.comps_service import query_transactions_sql, semantic_rerank


def comps_agent_node(state: DealState) -> DealState:
    state.trace("comps", "running")
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
    return state

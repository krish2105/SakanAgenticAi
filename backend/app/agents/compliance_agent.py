"""Agent 4 — Compliance RAG Agent (ARCHITECTURE.md Section 5.5). Claude Sonnet.

The core differentiator: every compliance claim must be grounded in a
retrieved clause. After the LLM responds, we programmatically verify that
every id in cited_clause_ids actually appears in retrieved_clauses. If not,
we reject and retry once, then fall back to an explicit "unable to verify"
result rather than surfacing an unverified claim. Same hallucination
guardrail pattern as ClaimGuard -- enforced in code, not just prompted.
"""
from __future__ import annotations

import json

from app.config import REASONING_MODEL
from app.deal_state import DealState
from app.llm import complete_json
from app.rag.retrieval import compose_retrieval_query, retrieve_clauses

SYSTEM_PROMPT = """You are the Compliance RAG Agent for Sakan AI. Ground every statement in the retrieved
regulatory clauses below — never state a compliance requirement that is not present in
the retrieved text. If the retrieved clauses do not clearly cover this deal, say so
explicitly rather than guessing.

Output JSON:
{
  "compliance_flags": [string],
  "compliance_summary": string,
  "cited_clause_ids": [string]
}
Every claim in compliance_summary MUST cite a clause_id from the retrieved clauses, and
cited_clause_ids MUST contain only clause_ids that were actually retrieved below.
"""

FALLBACK_SUMMARY = "unable to verify — recommend manual RERA check"


def _attempt_llm_compliance(deal_context: str, retrieved_clauses: list[dict]) -> dict:
    user_content = (
        f"DEAL CONTEXT: {deal_context}\n"
        f"RETRIEVED CLAUSES:\n{json.dumps(retrieved_clauses, indent=2)}"
    )
    result = complete_json(SYSTEM_PROMPT, user_content, model=REASONING_MODEL)

    valid_ids = {c["clause_id"] for c in retrieved_clauses}
    cited = set(result.get("cited_clause_ids") or [])
    if not cited or not cited.issubset(valid_ids):
        raise ValueError(
            f"cited_clause_ids {sorted(cited)} not a subset of retrieved clause_ids {sorted(valid_ids)}"
        )
    return result


def compliance_agent_node(state: DealState) -> DealState:
    state.trace("compliance", "running")

    is_off_plan = bool(state.project_id) or "off-plan" in state.raw_query.lower() or "off plan" in state.raw_query.lower()
    query_text = compose_retrieval_query(state.property_type, state.community, is_off_plan, state.raw_query)

    try:
        retrieved = retrieve_clauses(query_text)
    except Exception as exc:  # noqa: BLE001
        state.retrieved_clauses = []
        state.compliance_flags = ["retrieval_unavailable"]
        state.compliance_summary = FALLBACK_SUMMARY
        state.trace("compliance", "done", detail=f"retrieval failed: {exc}")
        return state

    state.retrieved_clauses = retrieved

    if not retrieved:
        state.compliance_flags = ["insufficient_retrieved_evidence"]
        state.compliance_summary = (
            "No regulatory clauses were retrieved for this deal — recommend manual RERA check."
        )
        state.trace("compliance", "done", detail="no clauses retrieved")
        return state

    deal_context = (
        f"community={state.community}, property_type={state.property_type}, "
        f"bedrooms={state.bedrooms}, off_plan={is_off_plan}, project_id={state.project_id}, "
        f"raw_query={state.raw_query!r}"
    )

    last_error: Exception | None = None
    for attempt_num in (1, 2):
        try:
            result = _attempt_llm_compliance(deal_context, retrieved)
            state.compliance_flags = result.get("compliance_flags", [])
            state.compliance_summary = result.get("compliance_summary")
            state.trace("compliance", "done", detail=f"verified on attempt {attempt_num}")
            return state
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    state.compliance_flags = ["citation_validation_failed"]
    state.compliance_summary = FALLBACK_SUMMARY
    state.trace("compliance", "done", detail=f"guardrail fallback after 2 attempts: {last_error}")
    return state

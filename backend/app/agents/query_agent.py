"""Agent 1 — Query Agent (ARCHITECTURE.md Section 5.2). Claude Haiku."""
from __future__ import annotations

from app.config import QUERY_MODEL
from app.deal_state import DealState
from app.llm import complete_json

SYSTEM_PROMPT = """You are the Query Agent for Sakan AI, a Dubai real-estate deal-intelligence system.
Extract structured filters from the user's natural-language query. Output ONLY valid JSON:

{
  "query_type": "comps_search" | "valuation" | "compliance_check" | "full_memo",
  "community": string | null,
  "property_type": "Apartment" | "Villa" | "Townhouse" | null,
  "bedrooms": number | null,
  "budget_min": number | null,
  "budget_max": number | null,
  "project_id": string | null
}

Infer query_type "full_memo" if the user asks for a report, memo, or "everything" about a
deal. Infer "compliance_check" if they mention RERA, Form A/B/F, escrow, or legality.
Otherwise default to "comps_search" if no valuation or compliance language is present.
"""

VALID_PROPERTY_TYPES = {"Apartment", "Villa", "Townhouse"}
VALID_QUERY_TYPES = {"comps_search", "valuation", "compliance_check", "full_memo"}


def query_agent_node(state: DealState) -> DealState:
    state.trace("query", "running")
    try:
        result = complete_json(SYSTEM_PROMPT, f"QUERY: {state.raw_query}", model=QUERY_MODEL)

        query_type = result.get("query_type")
        state.query_type = query_type if query_type in VALID_QUERY_TYPES else "comps_search"

        property_type = result.get("property_type")
        state.property_type = property_type if property_type in VALID_PROPERTY_TYPES else None

        state.community = result.get("community") or None
        state.bedrooms = result.get("bedrooms")
        state.budget_min = result.get("budget_min")
        state.budget_max = result.get("budget_max")
        state.project_id = result.get("project_id") or None

        state.trace("query", "done", detail=f"query_type={state.query_type}")
    except Exception as exc:  # noqa: BLE001
        state.query_type = "comps_search"
        state.trace("query", "error", detail=str(exc))
    return state

"""Agent 1 — Query Agent (ARCHITECTURE.md Section 5.2). Claude Haiku."""
from __future__ import annotations

import re

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

# Dubai communities present in the synthetic seed dataset (seed_data/transactions.csv)
# and the DLD-mapped dataset alike -- used for a plain substring match when no LLM
# is available to extract this from free text.
KNOWN_COMMUNITIES = [
    "Al Barari", "Al Furjan", "Arabian Ranches", "Business Bay", "DAMAC Hills",
    "Downtown Dubai", "Dubai Hills Estate", "Dubai Marina", "Dubai Silicon Oasis",
    "Dubai South", "Jumeirah Lake Towers", "Jumeirah Village Circle",
    "Mohammed Bin Rashid City", "Motor City", "Palm Jumeirah",
]


def _heuristic_parse(raw_query: str) -> dict:
    """Same classification rules as SYSTEM_PROMPT, applied with plain
    keyword/regex matching instead of an LLM call. Used when no
    ANTHROPIC_API_KEY is configured (a genuinely free/no-cost deployment)
    so the pipeline still routes to valuation/compliance/memo instead of
    query_agent's failure silently forcing every query down the
    comps_search short-circuit path (see graph.py's _route_after_comps)
    regardless of what was actually asked."""
    text = raw_query.lower()

    if any(kw in text for kw in ("report", "memo", "everything")):
        query_type = "full_memo"
    elif any(kw in text for kw in ("rera", "form a", "form b", "form f", "escrow", "legal", "compliance", "compliant")):
        query_type = "compliance_check"
    elif any(kw in text for kw in ("value", "worth", "valuation", "price range", "how much")):
        query_type = "valuation"
    else:
        query_type = "comps_search"

    property_type = None
    if "villa" in text:
        property_type = "Villa"
    elif "townhouse" in text:
        property_type = "Townhouse"
    elif "apartment" in text or "apt" in text or re.search(r"\bflat\b", text):
        property_type = "Apartment"

    bedrooms = None
    if re.search(r"\bstudio\b", text):
        bedrooms = 0
    else:
        br_match = re.search(r"(\d+)\s*(?:br|bed(?:room)?s?)\b", text)
        if br_match:
            bedrooms = int(br_match.group(1))

    community = next((c for c in KNOWN_COMMUNITIES if c.lower() in text), None)

    budget_min = budget_max = None
    amount_match = re.search(r"aed\s*([\d,.]+)\s*(m|million|k|thousand)?", text)
    if amount_match:
        amount = float(amount_match.group(1).replace(",", ""))
        unit = amount_match.group(2)
        if unit in ("m", "million"):
            amount *= 1_000_000
        elif unit in ("k", "thousand"):
            amount *= 1_000
        if any(kw in text for kw in ("under", "below", "max", "up to")):
            budget_max = amount
        elif any(kw in text for kw in ("over", "above", "min", "at least")):
            budget_min = amount
        else:
            budget_max = amount

    return {
        "query_type": query_type,
        "property_type": property_type,
        "bedrooms": bedrooms,
        "community": community,
        "budget_min": budget_min,
        "budget_max": budget_max,
    }


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
        parsed = _heuristic_parse(state.raw_query)
        state.query_type = parsed["query_type"]
        state.property_type = parsed["property_type"]
        state.bedrooms = parsed["bedrooms"]
        state.community = parsed["community"]
        state.budget_min = parsed["budget_min"]
        state.budget_max = parsed["budget_max"]
        state.trace("query", "done", detail=f"llm fallback: {exc}; heuristic query_type={state.query_type}")
    return state

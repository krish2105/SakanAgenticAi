"""Agent 3 — Valuation Agent (ARCHITECTURE.md Section 5.4). Claude Sonnet."""
from __future__ import annotations

import json

from app.config import REASONING_MODEL
from app.deal_state import DealState
from app.llm import complete_json

SYSTEM_PROMPT = """You are the Valuation Agent for Sakan AI. Given the comparable transactions below, compute
a fair-value range for the subject deal. You MUST base your range only on the comps
provided — do not invent market knowledge not present in the data.

Output JSON:
{
  "valuation_low": number,
  "valuation_high": number,
  "valuation_method": string,
  "valuation_rationale": string
}
The valuation_rationale MUST reference specific comp transaction_ids used.
"""


def _fallback_valuation(state: DealState) -> None:
    """Deterministic comp-median fallback used when the LLM call fails or
    no comps are available -- keeps the pipeline usable without an API key
    and gives the Valuation Agent a defined behavior on empty comp sets."""
    prices = [c["price"] for c in state.retrieved_comps if c.get("price") is not None]
    if not prices:
        state.valuation_low = None
        state.valuation_high = None
        state.valuation_method = "no comps available — unable to compute a range"
        state.valuation_rationale = "No comparable transactions were retrieved for this query."
        return

    prices.sort()
    median = prices[len(prices) // 2]
    state.valuation_low = round(median * 0.93, 2)
    state.valuation_high = round(median * 1.07, 2)
    ids = ", ".join(c["transaction_id"] for c in state.retrieved_comps[:6] if c.get("transaction_id"))
    state.valuation_method = f"median of {len(prices)} comps, +/-7% band (fallback heuristic, no LLM)"
    state.valuation_rationale = f"Median price across comps {ids}."


def valuation_agent_node(state: DealState) -> DealState:
    state.trace("valuation", "running")

    if not state.retrieved_comps:
        _fallback_valuation(state)
        state.trace("valuation", "done", detail="no comps")
        return state

    user_content = (
        f"COMPS (price, price_per_sqft, date):\n{json.dumps(state.retrieved_comps, indent=2)}\n\n"
        f"SUBJECT: {state.community}, {state.property_type}, {state.bedrooms}BR, "
        f"budget AED {state.budget_min}-{state.budget_max}"
    )

    try:
        result = complete_json(SYSTEM_PROMPT, user_content, model=REASONING_MODEL)
        state.valuation_low = result.get("valuation_low")
        state.valuation_high = result.get("valuation_high")
        state.valuation_method = result.get("valuation_method")
        state.valuation_rationale = result.get("valuation_rationale")
        state.trace("valuation", "done")
    except Exception as exc:  # noqa: BLE001
        _fallback_valuation(state)
        state.trace("valuation", "done", detail=f"llm fallback: {exc}")

    return state

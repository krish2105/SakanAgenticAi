"""Agent 3 — Valuation Agent (ARCHITECTURE.md Section 5.4). Claude Sonnet."""
from __future__ import annotations

import json
import statistics

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
    """Deterministic comp-based fallback used when the LLM call fails or
    no comps are available -- keeps the pipeline usable without an API key
    and gives the Valuation Agent a defined behavior on empty comp sets.

    Uses the comps' own P25-P75 spread (with a small pad) rather than a
    fixed +/-7% band around the median. The eval suite's
    valuation_band_coverage metric (scripts/run_evals.py) caught the fixed
    band systematically missing the real held-out sale price: this
    dataset -- and comp sets in general -- can have wide intra-scenario
    price variance a flat percentage doesn't track. Falls back to a wider
    fixed band when there are too few comps (<4) for a stable percentile
    estimate.
    """
    prices = [c["price"] for c in state.retrieved_comps if c.get("price") is not None]
    if not prices:
        state.valuation_low = None
        state.valuation_high = None
        state.valuation_method = "no comps available — unable to compute a range"
        state.valuation_rationale = "No comparable transactions were retrieved for this query."
        return

    prices.sort()
    n = len(prices)

    if n >= 4:
        q1, q3 = statistics.quantiles(prices, n=4)[0], statistics.quantiles(prices, n=4)[2]
        iqr = q3 - q1
        low = max(0.0, q1 - 0.15 * iqr)
        high = q3 + 0.15 * iqr
        method_detail = f"P25-P75 of {n} comps +/-15% IQR pad (fallback heuristic, no LLM)"
    else:
        median = prices[n // 2]
        low, high = median * 0.85, median * 1.15
        method_detail = f"median of {n} comps, +/-15% band (fallback heuristic, no LLM, n<4)"

    state.valuation_low = round(low, 2)
    state.valuation_high = round(high, 2)
    ids = ", ".join(c["transaction_id"] for c in state.retrieved_comps[:6] if c.get("transaction_id"))
    state.valuation_method = method_detail
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

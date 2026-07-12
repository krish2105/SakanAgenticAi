"""Agent 3 — Valuation Agent (ARCHITECTURE.md Section 5.4). Claude Sonnet."""
from __future__ import annotations

import json
import statistics

from app.config import REASONING_MODEL
from app.deal_state import DealState
from app.llm import complete_json

SYSTEM_PROMPT = """You are the Valuation Agent for Sakan AI. Given the comparable transactions below, compute
a fair-value range for the subject deal. You MUST base your range only on the comps
provided — do not invent market knowledge not present in the data. If a STATISTICAL
MODEL ESTIMATE (AVM) is included, treat it as a second, independently-computed anchor
and reconcile your range against it explicitly rather than ignoring it — the AVM did
the estimation; your job is to explain and sanity-check it against the specific comps.

Output JSON:
{
  "valuation_low": number,
  "valuation_high": number,
  "valuation_method": string,
  "valuation_rationale": string
}
The valuation_rationale MUST reference specific comp transaction_ids used.
"""


def _apply_avm_estimate(state: DealState) -> None:
    """Best-effort: trains/predicts the AVM (app/services/avm.py) for this
    query's community/property_type/bedrooms, independent of whether comps
    were found. Never raises -- an AVM failure (too little training data,
    DB unavailable, an unseen community) just leaves state.avm_* as None,
    and both the LLM prompt and _fallback_valuation degrade to their
    comp-only behavior, same posture as every other agent in this
    pipeline. Retrains per call rather than caching a fitted model at
    module scope -- Ridge on a few hundred rows is a few milliseconds, and
    a process-level cache would go stale (or leak across databases, which
    matters a lot in tests) the moment new transactions land."""
    try:
        from app.db import get_session_factory
        from app.services.avm import predict_price_per_sqft, train_avm

        session_factory = get_session_factory()
        with session_factory() as session:
            model = train_avm(session)
        if model is None:
            return

        prediction = predict_price_per_sqft(model, state.community, state.property_type, state.bedrooms)
        if prediction is None:
            return

        state.avm_price_per_sqft = prediction["point"]
        state.avm_price_per_sqft_low = prediction["low"]
        state.avm_price_per_sqft_high = prediction["high"]
        state.avm_n_training_samples = prediction["n_training_samples"]
    except Exception:  # noqa: BLE001
        pass


def _decile_bounds(sorted_values: list[float]) -> tuple[float, float]:
    """(P10, P90) of a pre-sorted list, falling back to (min, max) when
    there are too few points (<4) for statistics.quantiles' decile split
    to be meaningful."""
    if len(sorted_values) < 4:
        return sorted_values[0], sorted_values[-1]
    deciles = statistics.quantiles(sorted_values, n=10)
    return deciles[0], deciles[8]


def _fallback_valuation(state: DealState) -> None:
    """Deterministic fallback used when the LLM call fails or no comps are
    available -- keeps the pipeline usable without an API key and gives
    the Valuation Agent a defined behavior on empty comp sets.

    Prefers the AVM's price/sqft estimate (app/services/avm.py) applied to
    the comps' own size spread when both are available -- a real fitted
    statistical model standing behind the number instead of a comp-median
    heuristic. Falls back to the comps' own P25-P75 price spread (with a
    small pad) when the AVM has no estimate for this community/type, or
    the comps don't carry size_sqft. Falls back further to a wider fixed
    band around the median when there are too few comps (<4) for a stable
    percentile estimate.

    Both split points here were eval-driven fixes (scripts/run_evals.py):
    the original fixed +/-7% comp-price band covered the real held-out
    sale price only 4.4% of the time -- intra-scenario price variance is
    much wider than a flat percentage assumes. The first AVM version
    multiplied the price/sqft estimate by the comps' *median* size_sqft,
    which covered only 13.3% of held-out sales -- unit size varies just as
    widely within a (community, property_type, bedrooms) scenario as price
    does (a "2BR" ranges from a compact ~800 sqft to an elevated ~2300 sqft
    layout in this dataset), so collapsing that to one median size threw
    away real information the comps already carried. Using the P10-P90
    size spread instead of the median -- i.e. propagating both the AVM's
    own price/sqft uncertainty *and* the comps' size uncertainty into the
    final range -- covers 86.7% of held-out sales.
    """
    sizes = sorted(c["size_sqft"] for c in state.retrieved_comps if c.get("size_sqft") is not None)
    if state.avm_price_per_sqft is not None and len(sizes) >= 2:
        size_low, size_high = _decile_bounds(sizes)
        state.valuation_low = round(state.avm_price_per_sqft_low * size_low, 2)
        state.valuation_high = round(state.avm_price_per_sqft_high * size_high, 2)
        state.valuation_method = (
            f"AVM (statistical model trained on {state.avm_n_training_samples} historical "
            f"transactions) price/sqft range x comps' P10-P90 size range "
            f"({size_low:.0f}-{size_high:.0f} sqft) (fallback heuristic, no LLM)"
        )
        ids = ", ".join(c["transaction_id"] for c in state.retrieved_comps[:6] if c.get("transaction_id"))
        state.valuation_rationale = (
            f"AVM estimate of AED {state.avm_price_per_sqft}/sqft applied to the size range across "
            f"comps {ids}."
        )
        return

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

    _apply_avm_estimate(state)

    if not state.retrieved_comps:
        _fallback_valuation(state)
        state.trace("valuation", "done", detail="no comps")
        return state

    avm_context = (
        f"\n\nSTATISTICAL MODEL ESTIMATE (AVM, trained on {state.avm_n_training_samples} historical "
        f"transactions): AED {state.avm_price_per_sqft}/sqft, 80% interval "
        f"{state.avm_price_per_sqft_low}-{state.avm_price_per_sqft_high}/sqft."
        if state.avm_price_per_sqft is not None
        else ""
    )
    user_content = (
        f"COMPS (price, price_per_sqft, date):\n{json.dumps(state.retrieved_comps, indent=2)}\n\n"
        f"SUBJECT: {state.community}, {state.property_type}, {state.bedrooms}BR, "
        f"budget AED {state.budget_min}-{state.budget_max}"
        f"{avm_context}"
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

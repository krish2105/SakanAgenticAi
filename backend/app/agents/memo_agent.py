"""Agent 5 — Memo Agent (ARCHITECTURE.md Section 5.6). Claude Sonnet."""
from __future__ import annotations

from app.config import REASONING_MODEL
from app.deal_state import DealState
from app.llm import complete_text

SYSTEM_PROMPT = """You are the Memo Agent for Sakan AI. Write a concise, professional deal memo in markdown
using ONLY the data provided below. Structure: Subject Summary, Comparable Transactions
(table), Valuation Range & Method, Compliance Notes (with clause citations), Recommendation.
Keep it under 400 words. Do not add any figures, comps, or regulatory claims not present
in the data below.
"""


def _fallback_memo(state: DealState) -> str:
    """Deterministic markdown memo assembled directly from DealState, used
    when no LLM is available or the call fails -- keeps every downstream
    figure/citation traceable to state with zero synthesis risk."""
    lines = [
        f"# Deal Memo — {state.community or 'Unspecified Community'}",
        "",
        "## Subject Summary",
        f"- Query: {state.raw_query}",
        f"- Property type: {state.property_type or 'n/a'}, Bedrooms: {state.bedrooms if state.bedrooms is not None else 'n/a'}",
        f"- Budget: AED {state.budget_min or 'n/a'} – {state.budget_max or 'n/a'}",
        "",
        "## Comparable Transactions",
    ]
    if state.retrieved_comps:
        lines.append("| Transaction ID | Building | Beds | Price (AED) | AED/sqft | Date |")
        lines.append("|---|---|---|---|---|---|")
        for c in state.retrieved_comps:
            lines.append(
                f"| {c.get('transaction_id')} | {c.get('building')} | {c.get('bedrooms')} | "
                f"{c.get('price')} | {c.get('price_per_sqft')} | {c.get('date')} |"
            )
    else:
        lines.append("No comparable transactions were retrieved.")

    lines += [
        "",
        "## Valuation Range & Method",
        f"AED {state.valuation_low:,.0f} – {state.valuation_high:,.0f}" if state.valuation_low and state.valuation_high else "Not available.",
        f"Method: {state.valuation_method or 'n/a'}",
        f"Rationale: {state.valuation_rationale or 'n/a'}",
        "",
        "## Compliance Notes",
        state.compliance_summary or "Not available.",
    ]
    if state.compliance_flags:
        lines.append(f"Flags: {', '.join(state.compliance_flags)}")

    lines += [
        "",
        "## Recommendation",
        "This memo is a demonstration of method, not a certified appraisal. "
        "Verify all figures and compliance claims independently before relying on them.",
    ]
    return "\n".join(lines)


def memo_agent_node(state: DealState) -> DealState:
    state.trace("memo", "running")

    deal_state_json = state.model_dump_json(indent=2)
    try:
        memo = complete_text(SYSTEM_PROMPT, f"DEAL STATE: {deal_state_json}", model=REASONING_MODEL)
        state.memo_markdown = memo
        state.trace("memo", "done")
    except Exception as exc:  # noqa: BLE001
        state.memo_markdown = _fallback_memo(state)
        state.trace("memo", "done", detail=f"llm fallback: {exc}")

    return state

"""DealState — the shared object every LangGraph node reads and writes.

Mirrors ARCHITECTURE.md Section 5.1 exactly.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DealState(BaseModel):
    query_id: str
    raw_query: str

    # Query Agent output
    query_type: Optional[Literal["comps_search", "valuation", "compliance_check", "full_memo"]] = None
    community: Optional[str] = None
    property_type: Optional[str] = None  # Apartment | Villa | Townhouse
    bedrooms: Optional[int] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    project_id: Optional[str] = None

    # Comps Agent output
    retrieved_comps: list[dict] = Field(default_factory=list)

    # Valuation Agent output
    valuation_low: Optional[float] = None
    valuation_high: Optional[float] = None
    valuation_method: Optional[str] = None
    valuation_rationale: Optional[str] = None

    # AVM (Phase D): a statistical model's price/sqft estimate, computed
    # independently of retrieved_comps and given to the LLM as a grounding
    # anchor ("layered on top for explanation" -- MVP roadmap). None when
    # there's too little training data or the community/type wasn't seen
    # in training (app/services/avm.py).
    avm_price_per_sqft: Optional[float] = None
    avm_price_per_sqft_low: Optional[float] = None
    avm_price_per_sqft_high: Optional[float] = None
    avm_n_training_samples: Optional[int] = None

    # Compliance RAG Agent output
    retrieved_clauses: list[dict] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    compliance_summary: Optional[str] = None

    # Memo Agent output
    memo_markdown: Optional[str] = None

    agent_trace: list[dict] = Field(default_factory=list)

    def trace(self, agent: str, status: str, **detail) -> None:
        entry = {"agent": agent, "status": status, **detail}
        self.agent_trace.append(entry)

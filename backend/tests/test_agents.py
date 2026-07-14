import app.agents.compliance_agent as compliance_agent_module
import app.agents.memo_agent as memo_agent_module
import app.agents.query_agent as query_agent_module
import app.agents.valuation_agent as valuation_agent_module
from app.agents.comps_agent import comps_agent_node
from app.agents.graph import build_graph
from app.deal_state import DealState

SAMPLE_CLAUSES = [
    {
        "clause_id": "ESCROW-1",
        "text": "No developer may collect any payment from a buyer outside of a project-specific escrow account.",
        "source_doc": "escrow_account_regulations.md",
        "doc_category": "escrow",
        "similarity": 0.91,
    },
    {
        "clause_id": "RERA-F-3",
        "text": "Each payment instalment under Form F must be tied to a verified construction-completion percentage.",
        "source_doc": "rera_form_f_sale_purchase_agreement.md",
        "doc_category": "sale_purchase_agreement",
        "similarity": 0.83,
    },
]


def test_query_agent_parses_llm_json(monkeypatch):
    def fake_complete_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "query_type": "valuation",
            "community": "Dubai Marina",
            "property_type": "Apartment",
            "bedrooms": 2,
            "budget_min": 1800000,
            "budget_max": 2200000,
            "project_id": None,
        }

    monkeypatch.setattr(query_agent_module, "complete_json", fake_complete_json)

    state = DealState(query_id="q1", raw_query="2BR Dubai Marina under 2.2M")
    result = query_agent_module.query_agent_node(state)

    assert result.query_type == "valuation"
    assert result.community == "Dubai Marina"
    assert result.bedrooms == 2
    assert result.agent_trace[-1]["status"] == "done"


def test_query_agent_falls_back_on_llm_error(monkeypatch):
    def raising(*a, **k):
        raise RuntimeError("no API key")

    monkeypatch.setattr(query_agent_module, "complete_json", raising)

    state = DealState(query_id="q2", raw_query="anything")
    result = query_agent_module.query_agent_node(state)

    assert result.query_type == "comps_search"
    # An LLM-unavailable fallback is a successful, documented degraded path
    # (matching valuation/compliance/memo's own fallback tracing) -- not a
    # pipeline error, so the UI shouldn't flag it as one.
    assert result.agent_trace[-1]["status"] == "done"
    assert "llm fallback" in result.agent_trace[-1]["detail"]


def test_comps_agent_hits_seeded_db(seeded_sqlite_db):
    state = DealState(
        query_id="q3",
        raw_query="2BR apartment in Dubai Marina",
        community="Dubai Marina",
        property_type="Apartment",
        bedrooms=2,
    )
    result = comps_agent_node(state)

    assert result.agent_trace[-1]["agent"] == "comps"
    assert result.agent_trace[-1]["status"] == "done"
    assert isinstance(result.retrieved_comps, list)
    for c in result.retrieved_comps:
        assert c["community"] == "Dubai Marina"
        assert c["property_type"] == "Apartment"
        assert c["bedrooms"] == 2


def test_valuation_agent_uses_llm_when_comps_present(monkeypatch):
    def fake_complete_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "valuation_low": 1900000,
            "valuation_high": 2100000,
            "valuation_method": "median of 2 comps within 1km, +/-5%",
            "valuation_rationale": "Based on TXN-001 and TXN-002.",
        }

    monkeypatch.setattr(valuation_agent_module, "complete_json", fake_complete_json)

    state = DealState(
        query_id="q4",
        raw_query="value this",
        retrieved_comps=[
            {"transaction_id": "TXN-001", "price": 1950000, "price_per_sqft": 1700, "date": "2026-05-01"},
            {"transaction_id": "TXN-002", "price": 2050000, "price_per_sqft": 1750, "date": "2026-05-15"},
        ],
    )
    result = valuation_agent_module.valuation_agent_node(state)

    assert result.valuation_low == 1900000
    assert result.valuation_high == 2100000
    assert "TXN-001" in result.valuation_rationale


def test_valuation_agent_fallback_when_llm_fails():
    state = DealState(
        query_id="q5",
        raw_query="value this",
        retrieved_comps=[
            {"transaction_id": "TXN-001", "price": 1000000, "date": "2026-05-01"},
            {"transaction_id": "TXN-002", "price": 1200000, "date": "2026-05-15"},
            {"transaction_id": "TXN-003", "price": 1100000, "date": "2026-05-20"},
        ],
    )
    # No ANTHROPIC_API_KEY set in the test environment -> complete_json raises -> fallback path.
    result = valuation_agent_module.valuation_agent_node(state)

    assert result.valuation_low is not None
    assert result.valuation_high is not None
    assert result.valuation_low < result.valuation_high
    assert "fallback" in result.valuation_method


def test_compliance_agent_accepts_valid_citations(monkeypatch):
    monkeypatch.setattr(
        compliance_agent_module, "retrieve_clauses", lambda query_text, **k: SAMPLE_CLAUSES
    )

    def fake_complete_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "compliance_flags": ["escrow_verification_required"],
            "compliance_summary": "Payments must route through escrow per ESCROW-1; instalments tied to milestones per RERA-F-3.",
            "cited_clause_ids": ["ESCROW-1", "RERA-F-3"],
        }

    monkeypatch.setattr(compliance_agent_module, "complete_json", fake_complete_json)

    state = DealState(query_id="q6", raw_query="check RERA compliance for this off-plan deal", project_id="PRJ-01")
    result = compliance_agent_module.compliance_agent_node(state)

    # SAMPLE_CLAUSES carries no review_status -- unreviewed_regulatory_corpus
    # rides along automatically (see compliance_agent._corpus_review_flag).
    assert result.compliance_flags == ["escrow_verification_required", compliance_agent_module.UNREVIEWED_CORPUS_FLAG]
    assert "ESCROW-1" in result.compliance_summary
    assert result.agent_trace[-1]["detail"].startswith("verified on attempt 1")


def test_compliance_agent_guardrail_rejects_unverified_citation_and_falls_back(monkeypatch):
    """The core hallucination guardrail: the LLM cites a clause_id that was
    never retrieved. Both attempts must be rejected programmatically and the
    agent must fall back to the explicit 'unable to verify' result -- never
    surface the unverified claim."""
    monkeypatch.setattr(
        compliance_agent_module, "retrieve_clauses", lambda query_text, **k: SAMPLE_CLAUSES
    )

    call_count = {"n": 0}

    def fake_complete_json(system_prompt, user_content, model, max_tokens=1024):
        call_count["n"] += 1
        return {
            "compliance_flags": ["form_f_needed"],
            "compliance_summary": "This deal requires Form G approval, per RERA-G-9.",
            "cited_clause_ids": ["RERA-G-9"],  # hallucinated -- not in SAMPLE_CLAUSES
        }

    monkeypatch.setattr(compliance_agent_module, "complete_json", fake_complete_json)

    state = DealState(query_id="q7", raw_query="check compliance")
    result = compliance_agent_module.compliance_agent_node(state)

    assert call_count["n"] == 2  # retried once
    assert result.compliance_summary == compliance_agent_module.FALLBACK_SUMMARY
    assert result.compliance_flags == ["citation_validation_failed", compliance_agent_module.UNREVIEWED_CORPUS_FLAG]
    assert "RERA-G-9" not in (result.compliance_summary or "")


def test_compliance_agent_no_retrieved_clauses_is_explicit():
    state = DealState(query_id="q8", raw_query="check compliance for a made-up scenario")
    # No monkeypatch of retrieve_clauses -> hits real Qdrant/embedder path, which
    # has no network access in this sandbox -> retrieval raises -> explicit fallback.
    result = compliance_agent_module.compliance_agent_node(state)

    assert result.compliance_flags in (["insufficient_retrieved_evidence"], ["retrieval_unavailable"])
    assert result.compliance_summary == compliance_agent_module.FALLBACK_SUMMARY


def test_corpus_review_flag_is_none_when_a_retrieved_clause_is_reviewed():
    reviewed_clauses = [{**SAMPLE_CLAUSES[0], "review_status": "reviewed", "reviewed_by": "Example Legal LLP"}, SAMPLE_CLAUSES[1]]
    assert compliance_agent_module._corpus_review_flag(reviewed_clauses) is None


def test_corpus_review_flag_fires_when_nothing_is_reviewed():
    assert compliance_agent_module._corpus_review_flag(SAMPLE_CLAUSES) == compliance_agent_module.UNREVIEWED_CORPUS_FLAG


def test_corpus_review_flag_is_none_for_empty_retrieval():
    assert compliance_agent_module._corpus_review_flag([]) is None


def test_memo_agent_fallback_produces_traceable_markdown():
    state = DealState(
        query_id="q9",
        raw_query="full memo",
        community="Business Bay",
        retrieved_comps=[{"transaction_id": "TXN-01", "building": "Executive Towers", "bedrooms": 2, "price": 1900000, "price_per_sqft": 1600, "date": "2026-04-01"}],
        valuation_low=1850000,
        valuation_high=1950000,
        valuation_method="median +/-5%",
        valuation_rationale="Based on TXN-01.",
        compliance_summary="No issues found per ESCROW-1.",
        compliance_flags=[],
    )
    result = memo_agent_module.memo_agent_node(state)

    assert result.memo_markdown is not None
    assert "TXN-01" in result.memo_markdown
    assert "Business Bay" in result.memo_markdown
    assert "1,850,000" in result.memo_markdown or "1850000" in result.memo_markdown


def test_full_graph_runs_end_to_end_for_comps_search(monkeypatch, seeded_sqlite_db):
    """comps_search should short-circuit straight to END after comps (the
    conditional-edge cost/latency optimization), never touching valuation,
    compliance, or memo."""

    def fake_query_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "query_type": "comps_search",
            "community": "Dubai Marina",
            "property_type": "Apartment",
            "bedrooms": 2,
            "budget_min": None,
            "budget_max": None,
            "project_id": None,
        }

    monkeypatch.setattr(query_agent_module, "complete_json", fake_query_json)

    graph = build_graph()
    result = graph.invoke(DealState(query_id="q10", raw_query="2BR Dubai Marina").model_dump())

    assert result["query_type"] == "comps_search"
    assert isinstance(result["retrieved_comps"], list)
    assert result["valuation_low"] is None
    assert result["memo_markdown"] is None
    done_agents = [t["agent"] for t in result["agent_trace"] if t["status"] == "done"]
    assert done_agents == ["query", "comps"]


def test_full_graph_runs_end_to_end_for_full_memo(monkeypatch, seeded_sqlite_db):
    def fake_query_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "query_type": "full_memo",
            "community": "Dubai Marina",
            "property_type": "Apartment",
            "bedrooms": 2,
            "budget_min": 1800000,
            "budget_max": 2200000,
            "project_id": None,
        }

    monkeypatch.setattr(query_agent_module, "complete_json", fake_query_json)
    monkeypatch.setattr(
        compliance_agent_module, "retrieve_clauses", lambda query_text, **k: SAMPLE_CLAUSES
    )

    def fake_compliance_json(system_prompt, user_content, model, max_tokens=1024):
        return {
            "compliance_flags": [],
            "compliance_summary": "No issues found per ESCROW-1.",
            "cited_clause_ids": ["ESCROW-1"],
        }

    monkeypatch.setattr(compliance_agent_module, "complete_json", fake_compliance_json)

    graph = build_graph()
    result = graph.invoke(DealState(query_id="q11", raw_query="full memo for a 2BR in Dubai Marina").model_dump())

    assert result["query_type"] == "full_memo"
    done_agents = [t["agent"] for t in result["agent_trace"] if t["status"] == "done"]
    assert done_agents == ["query", "comps", "valuation", "compliance", "memo"]
    assert result["memo_markdown"] is not None
    assert result["compliance_summary"] == "No issues found per ESCROW-1."

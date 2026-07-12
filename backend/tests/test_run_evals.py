import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_engine, get_session_factory  # noqa: E402
from scripts.run_evals import (  # noqa: E402
    eval_citation_guardrail,
    eval_comps_relevance,
    eval_valuation_accuracy,
    load_scenarios,
    main,
)


def test_load_scenarios_and_comps_relevance_against_seeded_data(seeded_sqlite_db):
    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        scenarios = load_scenarios(session, min_transactions=2, max_scenarios=5)
        assert len(scenarios) > 0

        result = eval_comps_relevance(session, scenarios)
        assert result["filter_accuracy"] == 1.0  # SQL WHERE clauses must never mismatch
        assert 0.0 <= result["coverage"] <= 1.0


def test_valuation_accuracy_reports_band_coverage_and_width(seeded_sqlite_db):
    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        scenarios = load_scenarios(session, min_transactions=4, max_scenarios=5)
        result = eval_valuation_accuracy(session, scenarios)
        assert result["n_evaluated"] > 0
        assert 0.0 <= result["band_coverage"] <= 1.0
        assert result["width_ratio"] > 0


def test_citation_guardrail_battery_all_correct():
    def patch_complete_json(fake_response):
        import app.agents.compliance_agent as compliance_agent_module

        compliance_agent_module.complete_json = lambda *a, **k: fake_response

    import app.agents.compliance_agent as compliance_agent_module

    original = compliance_agent_module.complete_json
    try:
        result = eval_citation_guardrail(patch_complete_json)
    finally:
        compliance_agent_module.complete_json = original

    assert result["accuracy"] == 1.0
    assert result["n_cases"] >= 4


def test_main_exits_zero_against_seeded_dataset(seeded_sqlite_db):
    exit_code = main(["--database-url", seeded_sqlite_db, "--skip-retrieval"])
    assert exit_code == 0

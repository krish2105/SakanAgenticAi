from app.db import get_engine, get_session_factory
from app.deal_state import DealState
from app.services.avm import predict_price_per_sqft, train_avm
import app.agents.valuation_agent as valuation_agent_module


def test_train_avm_returns_none_with_too_little_data(seeded_sqlite_db):
    """MIN_TRAINING_ROWS=30 -- a handful of rows shouldn't produce a model
    a caller might mistake for something trained on real signal."""
    import app.services.avm as avm_module

    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        original_min = avm_module.MIN_TRAINING_ROWS
        avm_module.MIN_TRAINING_ROWS = 10_000  # force the "too little data" branch
        try:
            model = train_avm(session)
        finally:
            avm_module.MIN_TRAINING_ROWS = original_min
    assert model is None


def test_train_avm_predicts_close_to_real_median(seeded_sqlite_db):
    """Sanity check against the seeded dataset's own numbers -- not just
    'it returns something', but 'the something is in the right ballpark'.
    This is the check that originally caught a real imputation bug (using
    a global median building price instead of a community-specific one
    biased every prediction toward the dataset-wide mean)."""
    import statistics

    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        model = train_avm(session)
        assert model is not None
        assert model.n_training_samples >= 30

        from sqlalchemy import select
        from app.models import Transaction

        rows = session.scalars(
            select(Transaction.price_per_sqft).where(
                Transaction.community == "Dubai Marina",
                Transaction.property_type == "Apartment",
                Transaction.bedrooms == 2,
            )
        ).all()
        actual_median = statistics.median(float(p) for p in rows)

        prediction = predict_price_per_sqft(model, "Dubai Marina", "Apartment", 2)

    assert prediction is not None
    # Within 20% of the real median -- a loose bound (this is a ~600-row
    # Ridge model, not meant to be exact), but tight enough to catch a
    # systematic-bias regression like the one this test caught originally.
    assert abs(prediction["point"] - actual_median) / actual_median < 0.20


def test_predict_returns_none_for_unseen_community(seeded_sqlite_db):
    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        model = train_avm(session)
        assert model is not None
    assert predict_price_per_sqft(model, "Nonexistent Community", "Apartment", 2) is None


def test_predict_returns_none_for_missing_fields(seeded_sqlite_db):
    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        model = train_avm(session)
        assert model is not None
    assert predict_price_per_sqft(model, None, "Apartment", 2) is None
    assert predict_price_per_sqft(model, "Dubai Marina", "Apartment", None) is None


def test_valuation_agent_uses_avm_in_fallback_when_available(seeded_sqlite_db):
    """End-to-end through the actual agent node (not just avm.py directly):
    no ANTHROPIC_API_KEY -> LLM path fails -> _fallback_valuation should
    prefer the AVM-derived range over the plain comp-percentile heuristic
    when the AVM has an estimate for this community/type/bedrooms."""
    state = DealState(
        query_id="avm-test",
        raw_query="2BR apartment in Dubai Marina",
        community="Dubai Marina",
        property_type="Apartment",
        bedrooms=2,
    )
    from app.agents.comps_agent import comps_agent_node

    state = comps_agent_node(state)
    assert state.retrieved_comps, "seeded dataset should have Dubai Marina 2BR comps"

    result = valuation_agent_module.valuation_agent_node(state)

    assert result.avm_price_per_sqft is not None
    assert result.avm_n_training_samples is not None and result.avm_n_training_samples >= 30
    assert result.valuation_low is not None and result.valuation_high is not None
    assert result.valuation_low < result.valuation_high
    assert "AVM" in result.valuation_method

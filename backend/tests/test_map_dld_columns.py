from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, Building, Transaction
from scripts.map_dld_columns import run

FIXTURE = Path(__file__).parent / "fixtures" / "dld_transactions_sample.csv"


def test_dry_run_stats():
    stats = run(FIXTURE, database_url=None, chunksize=1000, dry_run=True, row_limit=None)

    assert stats.rows_read == 12
    assert stats.dropped_not_sale == 2  # 1 mortgage + 1 gift
    assert stats.dropped_not_residential == 2  # 1 commercial usage + 1 land subtype
    assert stats.dropped_placeholder == 2  # 1 AED + sub-0.01sqm
    assert stats.dropped_unparseable_date == 1
    assert stats.dropped_duplicate == 1
    assert stats.rows_loaded == 4  # TXN1, TXN2, TXN3, TXN10


def test_loads_into_database(tmp_path):
    db_path = tmp_path / "sakan_test.db"
    database_url = f"sqlite:///{db_path}"

    stats = run(FIXTURE, database_url=database_url, chunksize=1000, dry_run=False, row_limit=None)
    assert stats.rows_loaded == 4

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        transactions = session.scalars(select(Transaction)).all()
        buildings = session.scalars(select(Building)).all()

        assert len(transactions) == 4
        assert {t.property_type for t in transactions} == {"Apartment", "Villa", "Townhouse"}
        # Phase D provenance tagging -- real DLD data via a Kaggle mirror,
        # not synthetic and not a licensed partnership feed.
        assert all(t.data_provenance == "dld_kaggle" for t in transactions)

        apartment = next(t for t in transactions if t.community == "Business Bay")
        assert apartment.property_type == "Apartment"
        assert apartment.bedrooms == 2
        assert float(apartment.price_aed) == 1850000.0
        assert float(apartment.size_sqft) == round(85.5 * 10.7639, 2)
        assert apartment.registration_type == "Title Deed"
        assert apartment.transaction_type == "Sale"

        off_plan = next(t for t in transactions if t.transaction_type == "Off-Plan")
        assert off_plan.registration_type == "Oqood"
        assert off_plan.property_type == "Townhouse"

        studio = next(t for t in transactions if t.bedrooms == 0)
        assert studio.property_type == "Apartment"

        assert len(buildings) >= 1
        assert any(b.name == "Marina Gate II" for b in buildings)

    # Re-running against the same DB should not duplicate rows (idempotent upsert).
    stats2 = run(FIXTURE, database_url=database_url, chunksize=1000, dry_run=False, row_limit=None)
    assert stats2.rows_loaded == 4
    with Session(engine) as session:
        assert len(session.scalars(select(Transaction)).all()) == 4

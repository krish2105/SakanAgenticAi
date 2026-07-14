from pathlib import Path

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.models import Building, Developer, OffPlanProject, Transaction
from scripts.generate_dataset import make_buildings, make_developers, make_off_plan_projects, make_transactions, TxnConfig
import random

from scripts.seed_db import run as seed_run


def test_generator_produces_consistent_foreign_keys():
    rng = random.Random(7)
    developers = make_developers(rng)
    buildings = make_buildings(rng, developers, count=20)
    off_plan = make_off_plan_projects(rng, developers, count=5)
    transactions = make_transactions(rng, buildings, TxnConfig(count=100))

    developer_ids = {d["developer_id"] for d in developers}
    building_ids = {b["building_id"] for b in buildings}

    assert len(developers) == 15
    assert len(buildings) == 20
    assert len(off_plan) == 5
    assert len(transactions) == 100

    assert all(b["developer_id"] in developer_ids for b in buildings)
    assert all(p["developer_id"] in developer_ids for p in off_plan)
    assert all(t["building_id"] in building_ids for t in transactions)
    assert all(t["property_type"] in {"Apartment", "Villa", "Townhouse"} for t in transactions)
    assert all(t["price_aed"] > 0 and t["size_sqft"] > 0 for t in transactions)


def test_seed_db_loads_generated_csvs(tmp_path):
    seed_dir = Path(__file__).resolve().parents[1] / "seed_data"
    required = ["developers.csv", "buildings.csv", "off_plan_projects.csv", "transactions.csv"]
    assert all((seed_dir / f).exists() for f in required), (
        "Run `python backend/scripts/generate_dataset.py` before this test."
    )

    db_path = tmp_path / "seed_test.db"
    database_url = f"sqlite:///{db_path}"

    counts = seed_run(seed_dir, database_url)
    assert counts["developers.csv"] == 15
    assert counts["buildings.csv"] == 80
    assert counts["off_plan_projects.csv"] == 20
    assert counts["transactions.csv"] == 600

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Developer)) == 15
        assert session.scalar(select(func.count()).select_from(Building)) == 80
        assert session.scalar(select(func.count()).select_from(OffPlanProject)) == 20
        assert session.scalar(select(func.count()).select_from(Transaction)) == 600
        # Default provenance for a plain seed_db.py load (Phase D).
        assert session.scalar(select(func.count()).select_from(Transaction).where(Transaction.data_provenance == "synthetic")) == 600

    # Re-seeding is idempotent (ON CONFLICT DO NOTHING).
    seed_run(seed_dir, database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Transaction)) == 600


def test_seed_db_tags_provenance_via_flag(tmp_path):
    seed_dir = Path(__file__).resolve().parents[1] / "seed_data"
    db_path = tmp_path / "seed_provenance_test.db"
    database_url = f"sqlite:///{db_path}"

    seed_run(seed_dir, database_url, provenance="dld_kaggle")

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        n = session.scalar(select(func.count()).select_from(Transaction).where(Transaction.data_provenance == "dld_kaggle"))
        assert n == 600


def test_seed_db_loads_transactions_via_dld_mapped_csv(tmp_path):
    """Phase 12a: seed_db.py's transaction step routes through
    app/services/data_source.py's DldKaggleDataSource when --dld-mapped-csv
    is given, instead of the default seed-dir/transactions.csv path --
    this is the one place in the codebase that actually exercises that
    class end-to-end (previously only its own unit test did)."""
    seed_dir = Path(__file__).resolve().parents[1] / "seed_data"
    db_path = tmp_path / "seed_dld_mapped_test.db"
    database_url = f"sqlite:///{db_path}"

    mapped_csv = tmp_path / "dld_mapped.csv"
    mapped_csv.write_text(
        "transaction_id,building_id,community,property_type,bedrooms,size_sqft,price_aed,"
        "price_per_sqft,transaction_type,transaction_date,registration_type,buyer_type\n"
        "TXN-DLD-001,BLDG-001,Dubai Marina,Apartment,2,1200,2500000,2083.33,Sale,2026-01-15,Off-Plan,Individual\n"
    )

    seed_run(seed_dir, database_url, dld_mapped_csv=mapped_csv)

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        # Only the one row from the mapped CSV -- not the 600-row synthetic
        # seed_dir/transactions.csv, confirming it really took the
        # DataSourceProvider path instead of the default.
        rows = session.scalars(select(Transaction)).all()
        assert len(rows) == 1
        assert rows[0].transaction_id == "TXN-DLD-001"
        assert rows[0].data_provenance == "dld_kaggle"
        assert rows[0].price_aed == 2500000.0


def test_seed_db_licensed_feed_flag_reaches_licensed_data_source(tmp_path, monkeypatch):
    """--licensed-feed with no LICENSED_DATA_FEED_URL configured must fail
    the same clear way calling LicensedFeedDataSource directly would --
    confirms the flag actually reaches that class, not a silent no-op."""
    seed_dir = Path(__file__).resolve().parents[1] / "seed_data"
    db_path = tmp_path / "seed_licensed_test.db"
    database_url = f"sqlite:///{db_path}"

    import app.services.data_source as data_source_module

    monkeypatch.setattr(data_source_module.config, "LICENSED_DATA_FEED_URL", None)

    try:
        seed_run(seed_dir, database_url, licensed_feed=True)
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "No licensed data partnership is configured" in str(exc)
    assert raised

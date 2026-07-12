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

    # Re-seeding is idempotent (ON CONFLICT DO NOTHING).
    seed_run(seed_dir, database_url)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Transaction)) == 600

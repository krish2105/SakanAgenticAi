#!/usr/bin/env python3
"""
Loads the synthetic seed CSVs (backend/seed_data/, produced by
generate_dataset.py) into Postgres, matching ARCHITECTURE.md Section 8.

Load order respects foreign keys: developers -> buildings ->
off_plan_projects -> transactions. Each table is upserted with
ON CONFLICT DO NOTHING, so re-running against the same data is safe.

Usage:
    python seed_db.py --seed-dir backend/seed_data
    python seed_db.py --seed-dir backend/seed_data --database-url postgresql+psycopg2://sakan:sakan@localhost:5432/sakan
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_engine  # noqa: E402
from app.models import Base, Developer, Building, OffPlanProject, Transaction  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def coerce_developer(row: dict) -> dict:
    return {
        "developer_id": row["developer_id"],
        "name": row["name"],
        "track_record_score": int(row["track_record_score"]),
        "active_projects_count": int(row["active_projects_count"]),
        "delivery_delay_rate": float(row["delivery_delay_rate"]),
    }


def coerce_building(row: dict) -> dict:
    return {
        "building_id": row["building_id"],
        "name": row["name"],
        "community": row["community"],
        "developer_id": row["developer_id"],
        "completion_status": row["completion_status"],
        "total_units": int(row["total_units"]),
        "avg_price_per_sqft": float(row["avg_price_per_sqft"]),
    }


def coerce_off_plan_project(row: dict) -> dict:
    return {
        "project_id": row["project_id"],
        "name": row["name"],
        "developer_id": row["developer_id"],
        "community": row["community"],
        "launch_date": date.fromisoformat(row["launch_date"]),
        "handover_date": date.fromisoformat(row["handover_date"]),
        "payment_plan_structure": row["payment_plan_structure"],
        "escrow_account_status": row["escrow_account_status"],
        "rera_registration_number": row["rera_registration_number"],
        "percent_sold": float(row["percent_sold"]),
    }


def coerce_transaction(row: dict, provenance: str = "synthetic") -> dict:
    return {
        "transaction_id": row["transaction_id"],
        "building_id": row["building_id"],
        "community": row["community"],
        "property_type": row["property_type"],
        "bedrooms": int(row["bedrooms"]),
        "size_sqft": float(row["size_sqft"]),
        "price_aed": float(row["price_aed"]),
        "price_per_sqft": float(row["price_per_sqft"]),
        "transaction_type": row["transaction_type"],
        "transaction_date": date.fromisoformat(row["transaction_date"]),
        "registration_type": row["registration_type"],
        "buyer_type": row["buyer_type"],
        # CSVs produced by map_dld_columns.py already carry their own
        # data_provenance column (tagged "dld_kaggle"); this default only
        # applies to the plain generate_dataset.py seed CSVs, which don't.
        "data_provenance": row.get("data_provenance") or provenance,
    }


def upsert(session, model, rows: list[dict], pk_col: str) -> int:
    if not rows:
        return 0
    from sqlalchemy.dialects import postgresql, sqlite

    dialect = session.get_bind().dialect.name
    insert_fn = postgresql.insert if dialect == "postgresql" else sqlite.insert

    stmt = insert_fn(model).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=[pk_col])
    session.execute(stmt)
    return len(rows)


def run(seed_dir: Path, database_url: str | None, provenance: str = "synthetic") -> dict[str, int]:
    engine = get_engine(database_url) if database_url else get_engine()
    Base.metadata.create_all(
        engine,
        tables=[Developer.__table__, Building.__table__, OffPlanProject.__table__, Transaction.__table__],
    )

    from sqlalchemy.orm import Session

    table_plan = [
        ("developers.csv", Developer, coerce_developer, "developer_id"),
        ("buildings.csv", Building, coerce_building, "building_id"),
        ("off_plan_projects.csv", OffPlanProject, coerce_off_plan_project, "project_id"),
        ("transactions.csv", Transaction, lambda r: coerce_transaction(r, provenance), "transaction_id"),
    ]

    counts: dict[str, int] = {}
    with Session(engine, future=True) as session:
        for filename, model, coerce, pk_col in table_plan:
            csv_path = seed_dir / filename
            if not csv_path.exists():
                raise SystemExit(f"Missing {csv_path}. Run generate_dataset.py first.")
            rows = [coerce(r) for r in read_csv(csv_path)]
            counts[filename] = upsert(session, model, rows, pk_col)
            session.commit()

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed-dir", type=Path, default=Path("backend/seed_data"))
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument(
        "--provenance",
        type=str,
        default="synthetic",
        choices=["synthetic", "dld_kaggle", "licensed_partner"],
        help="Tags every loaded transaction's data_provenance column (ignored for rows whose CSV already sets one, e.g. map_dld_columns.py's output).",
    )
    args = parser.parse_args()

    counts = run(args.seed_dir, args.database_url, args.provenance)
    for filename, n in counts.items():
        print(f"{filename}: {n} rows upserted")


if __name__ == "__main__":
    main()

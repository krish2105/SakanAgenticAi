#!/usr/bin/env python3
"""
Adds the `data_provenance` column to an existing `transactions` table that
predates it, backfilling every existing row as 'synthetic' (the only
source this repo has ever shipped with by default).

Same category of gap as the earlier owner_id and billing-column incidents:
this repo has no Alembic wired up, so Base.metadata.create_all() only
creates missing *tables*, never alters an existing one. Idempotent --
ADD COLUMN IF NOT EXISTS is safe to re-run.

Usage:
    python migrate_add_data_provenance.py
    python migrate_add_data_provenance.py --database-url postgresql+psycopg2://...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.db import get_engine  # noqa: E402

STATEMENTS = [
    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS data_provenance VARCHAR(20) NOT NULL DEFAULT 'synthetic'",
]


def migrate(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            conn.execute(text(stmt))
    print(f"Applied {len(STATEMENTS)} data_provenance migration statement(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", type=str, default=None)
    args = parser.parse_args()
    migrate(args.database_url)


if __name__ == "__main__":
    main()

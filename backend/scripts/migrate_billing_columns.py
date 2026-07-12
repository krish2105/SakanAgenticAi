#!/usr/bin/env python3
"""
Adds the billing columns (tier, stripe_customer_id, stripe_subscription_id,
subscription_status) to an existing `users` table that predates them.

This repo has no Alembic wired up (a known gap -- see README), so
Base.metadata.create_all() only creates missing *tables*, never alters an
existing one. That already bit this project once (deal_queries.owner_id on
a live Render deployment, see README "Status"). Run this once against any
Postgres database that had `users` created before this change; fresh
databases don't need it since create_all() already includes these columns.

Idempotent: uses ADD COLUMN IF NOT EXISTS, safe to re-run.

Usage:
    python migrate_billing_columns.py
    python migrate_billing_columns.py --database-url postgresql+psycopg2://...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.db import get_engine  # noqa: E402

STATEMENTS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tier VARCHAR(20) NOT NULL DEFAULT 'starter'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(30)",
    "CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users (stripe_customer_id)",
]


def migrate(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            conn.execute(text(stmt))
    print(f"Applied {len(STATEMENTS)} billing-column migration statements.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", type=str, default=None)
    args = parser.parse_args()
    migrate(args.database_url)


if __name__ == "__main__":
    main()

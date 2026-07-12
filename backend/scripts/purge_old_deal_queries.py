#!/usr/bin/env python3
"""
Deletes deal_queries (and their audit_log rows) older than a retention
window. Addresses the gap flagged in the MVP roadmap: `deal_queries.raw_query`
and `deal_state` can contain user-entered PII (buyer names, budgets, deal
context) with no expiry, which is not defensible once real users are in the
system -- see README "Data retention" for the policy this script implements.

This script does the deleting; it does not schedule itself. Run it on a
recurring schedule (e.g. a Render Cron Job, a GitHub Actions scheduled
workflow, or a plain crontab entry) -- there is no scheduler wired into this
repo yet.

Usage:
    python purge_old_deal_queries.py --retention-days 180
    python purge_old_deal_queries.py --retention-days 180 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.db import get_engine, get_session_factory  # noqa: E402
from app.models import AuditLog, DealQuery  # noqa: E402

DEFAULT_RETENTION_DAYS = int(os.environ.get("PII_RETENTION_DAYS", 180))


def find_expired_query_ids(session, cutoff: datetime) -> list[int]:
    return list(session.scalars(select(DealQuery.query_id).where(DealQuery.created_at < cutoff)))


def purge(retention_days: int, dry_run: bool, database_url: str | None = None) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    session_factory = get_session_factory(get_engine(database_url) if database_url else None)

    with session_factory() as session:
        expired_ids = find_expired_query_ids(session, cutoff)
        if not expired_ids:
            return 0
        if dry_run:
            return len(expired_ids)

        session.execute(delete(AuditLog).where(AuditLog.query_id.in_(expired_ids)))
        session.execute(delete(DealQuery).where(DealQuery.query_id.in_(expired_ids)))
        session.commit()
        return len(expired_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Delete deal_queries older than this many days (default: {DEFAULT_RETENTION_DAYS}, "
        "or $PII_RETENTION_DAYS if set)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report how many rows would be deleted, delete nothing")
    parser.add_argument("--database-url", type=str, default=None)
    args = parser.parse_args()

    n = purge(args.retention_days, args.dry_run, args.database_url)
    verb = "Would delete" if args.dry_run else "Deleted"
    print(f"{verb} {n} deal_queries (and their audit_log rows) older than {args.retention_days} days.")


if __name__ == "__main__":
    main()

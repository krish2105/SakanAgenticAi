#!/usr/bin/env python3
"""
Sends an email digest for every saved search that currently has matches,
respecting a minimum resend interval (see alerts_service.MIN_DIGEST_INTERVAL)
so a rerun doesn't spam users with duplicates.

This is a digest of what currently matches, not a "new listing" alert --
Transaction has no insertion timestamp, so there's no honest way to prove a
match is genuinely new since the last check (see app/models.py's SavedSearch
docstring). Requires EMAIL_PROVIDER/RESEND_API_KEY (or SMTP_*) configured;
falls back to EMAIL_PROVIDER=console (logs instead of sending) same as every
other transactional email in this app.

This script does the sending; it does not schedule itself. Run it on a
recurring schedule (see .github/workflows/send-search-digests.yml).

Usage:
    python send_search_digests.py
    python send_search_digests.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_engine, get_session_factory  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.alerts_service import run_all_digests  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument(
        "--dry-run", action="store_true", help="Report how many saved searches currently have matches, send nothing"
    )
    args = parser.parse_args()

    engine = get_engine(args.database_url) if args.database_url else get_engine()
    Base.metadata.create_all(engine, checkfirst=True)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        if args.dry_run:
            from app.models import SavedSearch
            from app.services.alerts_service import matching_comps_for_search

            n = sum(1 for s in session.query(SavedSearch).all() if matching_comps_for_search(session, s))
            print(f"Would send {n} digest(s) (dry run -- nothing sent).")
            return

        sent = run_all_digests(session)
        print(f"Sent {sent} saved-search digest(s).")


if __name__ == "__main__":
    main()

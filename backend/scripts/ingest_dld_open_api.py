#!/usr/bin/env python3
"""
Ingests Dubai Land Department transaction data directly from Dubai Pulse's
official open-data API (dubaipulse.gov.ae) -- the government's own public
dataset, free, no licensed partnership needed. Complements
map_dld_columns.py's Kaggle-mirror path with a source one step closer to
the origin: tagged data_provenance="dld_open_free" instead of "dld_kaggle"
so a consumer can tell "we called DLD's own API" apart from "we downloaded
a third-party CSV copy of the same dataset."

IMPORTANT -- built from Dubai Pulse's published API documentation, NOT
verified against a live account: this sandbox has no network path to
dubaipulse.gov.ae/api.dubaipulse.gov.ae to test against (same posture as
LicensedFeedDataSource and the WhatsApp integration elsewhere in this repo
-- built correctly per the vendor's documented contract, covered by tests
that mock the HTTP layer, not exercised against the real service). Get an
account and dataset grant at dubaipulse.gov.ae first; you'll receive an API
Key and API Secret by email. Before relying on this in production, run
--dry-run once and check the resolved column mapping log line matches what
your account's response actually contains -- Dubai Pulse's field names are
documented to match the "dld_transactions-open" schema that
map_dld_columns.py's COLUMN_CANDIDATES already covers, but a live response
is the only way to be certain.

Auth flow (per Dubai Pulse's API Gateway docs): exchange DLD_OPEN_DATA_API_KEY
+ DLD_OPEN_DATA_API_SECRET for a short-lived (~30 min) bearer token via the
OAuth2 client-credentials endpoint, then call the transactions endpoint with
that token. A fresh token is fetched once per run (batch ingestion, not a
long-lived service -- no mid-run refresh needed for a single reasonably-sized
pull).

Reuses map_dld_columns.py's column-resolution and cleaning pipeline (same
canonical field names, same residential/placeholder/dedup filtering) instead
of duplicating it -- writes the fetched rows to a temp CSV shaped like the
Kaggle mirror's raw export, then delegates to map_dld_columns.run().

Usage:
    export DLD_OPEN_DATA_API_KEY=...
    export DLD_OPEN_DATA_API_SECRET=...
    python ingest_dld_open_api.py --limit 5000
    python ingest_dld_open_api.py --dry-run --limit 100
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from scripts.map_dld_columns import run as map_dld_run  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest_dld_open_api")

OAUTH_TOKEN_URL = "https://api.dubaipulse.gov.ae/oauth/client_credential/accesstoken"
TRANSACTIONS_URL = "https://api.dubaipulse.gov.ae/open/dld/dld_transactions-open-api"
PAGE_SIZE = 1000


def _get_access_token(api_key: str, api_secret: str) -> str:
    import httpx

    response = httpx.post(
        OAUTH_TOKEN_URL,
        params={"grant_type": "client_credentials"},
        data={"client_id": api_key, "client_secret": api_secret},
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError(f"Dubai Pulse OAuth response had no access_token: {response.text[:500]}")
    return token


def _fetch_pages(access_token: str, row_limit: int | None):
    """Yields raw transaction dicts, paginated. Offset/limit is the common
    convention for these open-data APIs; adjust here if a live account's
    response includes a different pagination shape (e.g. a cursor/next-page
    token) -- this is exactly the kind of detail that can only be confirmed
    against a real account, flagged prominently in this file's docstring."""
    import httpx

    fetched = 0
    offset = 0
    headers = {"Authorization": f"Bearer {access_token}"}

    with httpx.Client(timeout=30) as client:
        while row_limit is None or fetched < row_limit:
            page_size = PAGE_SIZE if row_limit is None else min(PAGE_SIZE, row_limit - fetched)
            response = client.get(
                TRANSACTIONS_URL, headers=headers, params={"limit": page_size, "offset": offset}
            )
            response.raise_for_status()
            page = response.json()
            rows = page.get("results", page) if isinstance(page, dict) else page
            if not rows:
                break
            for row in rows:
                yield row
            fetched += len(rows)
            offset += len(rows)
            if len(rows) < page_size:
                break  # short page -- reached the end


def run(
    database_url: str | None,
    dry_run: bool,
    row_limit: int | None,
    api_key: str | None = None,
    api_secret: str | None = None,
):
    api_key = api_key or config.DLD_OPEN_DATA_API_KEY
    api_secret = api_secret or config.DLD_OPEN_DATA_API_SECRET
    if not api_key or not api_secret:
        raise SystemExit(
            "DLD_OPEN_DATA_API_KEY / DLD_OPEN_DATA_API_SECRET are not set. Register at "
            "dubaipulse.gov.ae and request the 'Transactions' dataset to receive them."
        )

    log.info("Requesting a Dubai Pulse access token...")
    token = _get_access_token(api_key, api_secret)

    with tempfile.NamedTemporaryFile(
        mode="w", newline="", suffix=".csv", delete=False, encoding="utf-8"
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer: csv.DictWriter | None = None
        rows_written = 0
        for row in _fetch_pages(token, row_limit):
            if writer is None:
                writer = csv.DictWriter(tmp, fieldnames=list(row.keys()))
                writer.writeheader()
            writer.writerow(row)
            rows_written += 1

    if rows_written == 0:
        tmp_path.unlink(missing_ok=True)
        log.warning("Dubai Pulse API returned no rows -- nothing to load.")
        return

    log.info("Fetched %d rows from Dubai Pulse; running them through map_dld_columns' pipeline...", rows_written)
    try:
        stats = map_dld_run(
            input_path=tmp_path,
            database_url=database_url,
            chunksize=50_000,
            dry_run=dry_run,
            row_limit=None,  # already limited via _fetch_pages
            provenance="dld_open_free",
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    log.info("Rows fetched:              %d", rows_written)
    log.info("Rows read:                 %d", stats.rows_read)
    log.info("Dropped (not a sale):      %d", stats.dropped_not_sale)
    log.info("Dropped (not residential): %d", stats.dropped_not_residential)
    log.info("Dropped (placeholder):     %d", stats.dropped_placeholder)
    log.info("Dropped (bad date):        %d", stats.dropped_unparseable_date)
    log.info("Dropped (duplicate):       %d", stats.dropped_duplicate)
    log.info("Buildings upserted:        %d", stats.buildings_upserted)
    log.info("Transactions loaded:       %d%s", stats.rows_loaded, " (dry-run, not written)" if dry_run else "")
    return stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report stats without writing to Postgres")
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N rows (testing)")
    args = parser.parse_args(argv)

    run(args.database_url, args.dry_run, args.limit)


if __name__ == "__main__":
    main()

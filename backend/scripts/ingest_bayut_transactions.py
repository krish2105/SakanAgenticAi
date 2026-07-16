#!/usr/bin/env python3
"""
Ingests real Dubai Land Department-derived sale transactions from the "UAE
Real Estate Data API" listed on RapidAPI (publisher: Data API Hub) --
a third party's resale of the DLD registry, not a Dubai Pulse government
channel or a licensed partnership, tagged data_provenance="dld_bayut" so a
consumer can tell it apart from both. Free tier, no business registration.

IMPORTANT -- built against one real, manually-captured example response
(a `Transactions` call for Dubai Marina, confirmed to carry a real
`transaction_date`, `price`, and `price_per_sqft` -- not listing/asking
prices), but this sandbox has no network path to rapidapi.com to run the
full ingestion end to end itself (same posture as the Dubai Pulse and
licensed-feed integrations elsewhere in this repo). Run with --dry-run
first and check the logged stats match expectations before writing to
Postgres.

Assumption worth re-checking against a larger live sample: this endpoint's
per-row `status` field ("Off-plan" seen in the captured example) is treated
as the off-plan/ready signal (mirrors DLD's own Oqood/Title-Deed split),
and rows are treated as sale transactions based on their price-per-sqft
magnitude being in a plausible sale range -- see MIN_PRICE_PER_SQFT below.
If a live run shows rental contracts leaking in (a price_per_sqft in the
low hundreds, not low-to-mid thousands), tighten that floor.

Prerequisite: run resolve_bayut_locations.py first to populate
bayut_location_ids.json with each tracked community's numeric location_id.

Usage:
    export RAPIDAPI_KEY=...
    python ingest_bayut_transactions.py --dry-run --max-requests 5
    python ingest_bayut_transactions.py --max-requests 300
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app import config  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.models import Base, Building, Transaction  # noqa: E402
from scripts.map_dld_columns import map_property_type, short_id, upsert_buildings, upsert_transactions  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest_bayut_transactions")

API_HOST = "uae-real-estate-data-api1.p.rapidapi.com"
TRANSACTIONS_URL = f"https://{API_HOST}/transactions"
LOCATION_IDS_PATH = Path(__file__).resolve().parent / "bayut_location_ids.json"

PAGE_SIZE_ITEMS = 15  # observed page size in the captured example response
MIN_PRICE_AED = 1000
MIN_SIZE_SQFT = 50
# A sale price/sqft in Dubai is realistically >= a few hundred AED even in
# the cheapest communities; a value below this is far more likely a leaked
# rental-per-sqft figure than an actual sale. See docstring assumption note.
MIN_PRICE_PER_SQFT = 300

FIELDS = [
    "transaction_id",
    "building_id",
    "building_name_resolved",
    "community",
    "property_type",
    "bedrooms",
    "size_sqft",
    "price_aed",
    "price_per_sqft",
    "transaction_type",
    "transaction_date",
    "registration_type",
    "buyer_type",
    "data_provenance",
]


@dataclass
class IngestStats:
    requests_made: int = 0
    rows_fetched: int = 0
    dropped_placeholder: int = 0
    dropped_low_price_per_sqft: int = 0
    dropped_unparseable_date: int = 0
    dropped_duplicate: int = 0
    buildings_upserted: int = 0
    rows_loaded: int = 0
    seen_ids: set = field(default_factory=set)


def _headers(api_key: str) -> dict:
    return {"x-rapidapi-host": API_HOST, "x-rapidapi-key": api_key}


def _find_attributes(payload, _depth: int = 0) -> dict | None:
    """The captured example response nests the useful payload as
    `data.data.attributes` (an extra layer versus the more common
    `data.attributes`) -- rather than hardcode a depth that might differ
    on other endpoints/pagination states, search a few levels down for the
    first dict that actually carries a `transactions` list."""
    if not isinstance(payload, dict) or _depth > 4:
        return None
    if isinstance(payload.get("transactions"), list):
        return payload
    for value in payload.values():
        found = _find_attributes(value, _depth + 1)
        if found is not None:
            return found
    return None


def _status_to_reg_type(status: str | None) -> tuple[str, str]:
    """Mirrors map_dld_columns.map_registration_type's (registration_type,
    transaction_type) pair, keyed off this API's `status` field instead of
    DLD's raw `reg_type`."""
    text = (status or "").lower()
    if "off" in text and "plan" in text:
        return "Oqood", "Off-Plan"
    return "Title Deed", "Sale"


def _fetch_community_pages(community: str, location_id, api_key: str, max_requests: int, stats: IngestStats):
    """Yields raw transaction dicts for one community, paginating until
    total_pages is exhausted or max_requests is hit."""
    import httpx

    page = 1
    total_pages = None
    with httpx.Client(timeout=30) as client:
        while total_pages is None or page <= total_pages:
            if stats.requests_made >= max_requests:
                log.warning("Hit --max-requests budget (%d); stopping mid-run.", max_requests)
                return
            response = client.get(
                TRANSACTIONS_URL,
                headers=_headers(api_key),
                params={"location_id": location_id, "page": page, "period": "1y", "sort": "newest"},
            )
            stats.requests_made += 1
            response.raise_for_status()
            payload = response.json()
            attributes = _find_attributes(payload) or {}
            rows = attributes.get("transactions", [])
            if not attributes:
                log.error(
                    "Could not find a 'transactions' list anywhere in the response for %r "
                    "(page %d). Raw payload:\n%s",
                    community,
                    page,
                    json.dumps(payload, indent=2)[:2000],
                )
                return
            if total_pages is None:
                summary = attributes.get("summary", {})
                total_pages = attributes.get("total_pages") or 1
                log.info(
                    "%-28s location_id=%-6s total_items=%s total_pages=%s avg_price_per_sqft=%s",
                    community,
                    location_id,
                    attributes.get("total_items"),
                    total_pages,
                    summary.get("sale_avg_price_per_sqft"),
                )
            if not rows:
                return
            for row in rows:
                row["_community"] = community
                yield row
            page += 1
            time.sleep(0.3)


def clean_row(row: dict, stats: IngestStats) -> dict | None:
    stats.rows_fetched += 1
    community = row["_community"]

    price = row.get("price")
    size = row.get("property_size")
    price_per_sqft = row.get("price_per_sqft")
    if not isinstance(price, (int, float)) or not isinstance(size, (int, float)):
        stats.dropped_placeholder += 1
        return None
    if price < MIN_PRICE_AED or size < MIN_SIZE_SQFT:
        stats.dropped_placeholder += 1
        return None
    if not isinstance(price_per_sqft, (int, float)):
        price_per_sqft = price / size
    if price_per_sqft < MIN_PRICE_PER_SQFT:
        stats.dropped_low_price_per_sqft += 1
        return None

    txn_date = pd.to_datetime(row.get("transaction_date"), errors="coerce")
    if pd.isna(txn_date):
        stats.dropped_unparseable_date += 1
        return None

    dedupe_key = str(row.get("id") or f"{row.get('location_id')}-{row.get('property_number')}-{row.get('transaction_date')}-{price}")
    if dedupe_key in stats.seen_ids:
        stats.dropped_duplicate += 1
        return None
    stats.seen_ids.add(dedupe_key)

    property_type = map_property_type(None, row.get("property_type"))
    if property_type is None:
        stats.dropped_placeholder += 1
        return None

    building_name = row.get("location_name") or "Unregistered Building"
    building_id = short_id(building_name, community, prefix="BLD-", width=10)
    transaction_id = short_id(dedupe_key, prefix="TXN-", width=15)
    registration_type, transaction_type = _status_to_reg_type(row.get("status"))

    bedrooms = row.get("bedrooms")
    bedrooms = int(bedrooms) if isinstance(bedrooms, (int, float)) else None

    return {
        "transaction_id": transaction_id,
        "building_id": building_id,
        "building_name_resolved": building_name,
        "community": community,
        "property_type": property_type,
        "bedrooms": bedrooms,
        "size_sqft": round(float(size), 2),
        "price_aed": round(float(price), 2),
        "price_per_sqft": round(float(price_per_sqft), 2),
        "transaction_type": transaction_type,
        "transaction_date": txn_date,
        "registration_type": registration_type,
        "buyer_type": None,
        "data_provenance": "dld_bayut",
    }


def run(database_url: str | None, dry_run: bool, max_requests: int, api_key: str | None = None) -> IngestStats:
    api_key = api_key or config.RAPIDAPI_KEY
    if not api_key:
        raise SystemExit("RAPIDAPI_KEY is not set. See this file's docstring for the RapidAPI signup steps.")

    if not LOCATION_IDS_PATH.exists():
        raise SystemExit(
            f"{LOCATION_IDS_PATH} not found -- run resolve_bayut_locations.py first to build the "
            "community -> location_id mapping."
        )
    location_ids: dict = json.loads(LOCATION_IDS_PATH.read_text())

    stats = IngestStats()
    cleaned_rows: list[dict] = []

    for community, location_id in location_ids.items():
        if stats.requests_made >= max_requests:
            log.warning("Request budget exhausted before reaching %r; stopping.", community)
            break
        for raw_row in _fetch_community_pages(community, location_id, api_key, max_requests, stats):
            cleaned = clean_row(raw_row, stats)
            if cleaned:
                cleaned_rows.append(cleaned)

    stats.rows_loaded = len(cleaned_rows)

    if not cleaned_rows:
        log.warning("No usable rows fetched -- nothing to load.")
        return stats

    df = pd.DataFrame(cleaned_rows)[FIELDS]

    if not dry_run:
        engine = get_engine(database_url) if database_url else get_engine()
        Base.metadata.create_all(engine, tables=[Building.__table__, Transaction.__table__])
        from sqlalchemy.orm import Session

        with Session(engine, future=True) as session:
            upsert_buildings(session, df, stats)
            upsert_transactions(session, df)
            session.commit()

    return stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report stats without writing to Postgres")
    parser.add_argument(
        "--max-requests",
        type=int,
        default=100,
        # Conservative default: free RapidAPI plans here run 500-900
        # req/month, shared with resolve_bayut_locations.py and any manual
        # testing. A weekly scheduled run at this default uses <=400/month,
        # leaving headroom. Pass a higher value for a one-off deeper backfill.
        help="Cap total API calls this run (free-tier monthly budget is shared across resolve + ingest runs)",
    )
    args = parser.parse_args(argv)

    stats = run(args.database_url, args.dry_run, args.max_requests)

    log.info("API requests made:             %d", stats.requests_made)
    log.info("Rows fetched:                  %d", stats.rows_fetched)
    log.info("Dropped (placeholder/invalid): %d", stats.dropped_placeholder)
    log.info("Dropped (price/sqft too low):  %d", stats.dropped_low_price_per_sqft)
    log.info("Dropped (bad date):            %d", stats.dropped_unparseable_date)
    log.info("Dropped (duplicate):           %d", stats.dropped_duplicate)
    log.info("Buildings upserted:            %d", stats.buildings_upserted)
    log.info("Transactions loaded:           %d%s", stats.rows_loaded, " (dry-run, not written)" if args.dry_run else "")


if __name__ == "__main__":
    main()

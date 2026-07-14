#!/usr/bin/env python3
"""
DLD transactions adapter for Sakan AI.

Replaces the synthetic `transactions.csv` described in ARCHITECTURE.md Section 7
with real Dubai Land Department transaction records (as mirrored by the Kaggle
dataset alexefimik/dubai-real-estate-transactions-dataset, itself a copy of the
"Transactions" open dataset published on Dubai Pulse).

What it does:
  1. Reads the raw CSV in chunks (the real DLD extract is 1M+ rows).
  2. Renames DLD's native columns onto the `transactions` table fields defined
     in ARCHITECTURE.md Section 8 (and the DealState comp shape in Section 5.1).
  3. Filters to residential SALE transactions only (drops mortgages, gifts,
     commercial/industrial/land parcels).
  4. Drops rows with known DLD data-entry artifacts: placeholder considerations
     (amount == 1 AED and similar near-zero values) and placeholder sizes
     (procedure_area < 0.01 sqm).
  5. Upserts a lightweight `buildings` row per (building name, community) so the
     transactions.building_id foreign key resolves, then upserts the cleaned
     transactions into Postgres.

Usage:
    python map_dld_columns.py --input ./data/transactions.csv
    python map_dld_columns.py --input ./data/transactions.csv --dry-run
    python map_dld_columns.py --input ./data/transactions.csv --database-url postgresql+psycopg2://sakan:sakan@localhost:5432/sakan

Getting the source CSV (per ARCHITECTURE.md):
    pip install kaggle --break-system-packages
    # place your kaggle.json API token in ~/.kaggle/
    kaggle datasets download -d alexefimik/dubai-real-estate-transactions-dataset -p ./data --unzip
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_engine  # noqa: E402
from app.models import Base, Building, Transaction  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("map_dld_columns")

SQM_TO_SQFT = 10.7639

# Known DLD data-entry artifacts (see ARCHITECTURE.md Section 5.7 task note).
MIN_WORTH_AED = 1.0        # amount == 1 AED placeholder considerations
MIN_SIZE_SQM = 0.01        # sub-0.01 sqm placeholder unit sizes

# Candidate raw column names (normalized: lowercase, spaces/hyphens -> "_").
# Covers the canonical Dubai Pulse "dld_transactions-open" headers plus common
# Kaggle-mirror variants (e.g. the "_en" suffix stripped, or humanized names).
COLUMN_CANDIDATES: dict[str, list[str]] = {
    "raw_id": ["transaction_id", "trans_id", "id"],
    "trans_group": ["trans_group_en", "trans_group", "transaction_group", "group_en"],
    "instance_date": ["instance_date", "transaction_date", "date", "trans_date"],
    "actual_worth": ["actual_worth", "trans_value", "amount", "worth", "price"],
    "meter_sale_price": ["meter_sale_price", "price_per_sqm", "meter_price"],
    "procedure_area": ["procedure_area", "area_sqm", "size", "size_sqm", "unit_area"],
    "property_type": ["property_type_en", "property_type"],
    "property_sub_type": ["property_sub_type_en", "property_subtype_en", "property_sub_type", "property_subtype"],
    "property_usage": ["property_usage_en", "property_usage", "usage_en"],
    "reg_type": ["reg_type_en", "reg_type", "registration_type_en"],
    "area_name": ["area_name_en", "area_name", "community", "area_en"],
    "building_name": ["building_name_en", "building_name", "building"],
    "project_name": ["project_name_en", "project_name"],
    "rooms": ["rooms_en", "rooms", "room_en", "bedrooms"],
}

RESIDENTIAL_SUBTYPE_MAP = [
    (re.compile(r"town\s*house|townhouse", re.I), "Townhouse"),
    (re.compile(r"villa", re.I), "Villa"),
    (re.compile(r"flat|apartment|unit|hotel\s*apartment", re.I), "Apartment"),
]


@dataclass
class LoadStats:
    rows_read: int = 0
    dropped_not_sale: int = 0
    dropped_not_residential: int = 0
    dropped_placeholder: int = 0
    dropped_unparseable_date: int = 0
    dropped_duplicate: int = 0
    rows_loaded: int = 0
    buildings_upserted: int = 0
    seen_raw_ids: set = field(default_factory=set)


def normalize_headers(columns: list[str]) -> dict[str, str]:
    """Map raw CSV header -> normalized snake_case key."""
    normalized = {}
    for col in columns:
        key = re.sub(r"[\s\-]+", "_", col.strip().lower())
        key = re.sub(r"[^a-z0-9_]", "", key)
        normalized[col] = key
    return normalized


def resolve_columns(raw_columns: list[str]) -> dict[str, str]:
    """For each canonical field, find the matching raw column name, if any."""
    header_map = normalize_headers(raw_columns)  # raw -> normalized
    normalized_to_raw = {v: k for k, v in header_map.items()}

    resolved: dict[str, str] = {}
    for canonical, candidates in COLUMN_CANDIDATES.items():
        for candidate in candidates:
            if candidate in normalized_to_raw:
                resolved[canonical] = normalized_to_raw[candidate]
                break
    return resolved


def short_id(*parts: str, prefix: str, width: int) -> str:
    digest = hashlib.sha1("|".join(p or "" for p in parts).encode()).hexdigest()
    return f"{prefix}{digest[: width - len(prefix)]}"


def map_property_type(sub_type: str | None, prop_type: str | None) -> str | None:
    text = f"{sub_type or ''} {prop_type or ''}"
    for pattern, label in RESIDENTIAL_SUBTYPE_MAP:
        if pattern.search(text):
            return label
    return None


def parse_bedrooms(rooms_raw: str | None) -> int | None:
    if not rooms_raw or not isinstance(rooms_raw, str):
        return None
    text = rooms_raw.strip().lower()
    if "studio" in text:
        return 0
    match = re.search(r"(\d+)\s*b", text)
    if match:
        return int(match.group(1))
    match = re.search(r"^(\d+)$", text)
    if match:
        return int(match.group(1))
    return None


def map_registration_type(reg_type: str | None) -> tuple[str, str]:
    """Returns (registration_type, transaction_type) for the DB row."""
    text = (reg_type or "").lower()
    if "off" in text and "plan" in text:
        return "Oqood", "Off-Plan"
    return "Title Deed", "Sale"


def clean_chunk(
    chunk: pd.DataFrame, colmap: dict[str, str], stats: LoadStats, provenance: str = "dld_kaggle"
) -> pd.DataFrame:
    df = chunk.rename(columns={raw: canonical for canonical, raw in colmap.items()})
    stats.rows_read += len(df)

    # 1. Residential SALE transactions only.
    if "trans_group" in df.columns:
        is_sale = df["trans_group"].astype(str).str.contains("sale|sell", case=False, na=False)
        stats.dropped_not_sale += int((~is_sale).sum())
        df = df[is_sale]

    if "property_usage" in df.columns:
        is_residential = df["property_usage"].astype(str).str.contains("residential", case=False, na=False)
        stats.dropped_not_residential += int((~is_residential).sum())
        df = df[is_residential]

    df = df.copy()
    df["property_type_clean"] = [
        map_property_type(sub, typ)
        for sub, typ in zip(
            df.get("property_sub_type", pd.Series([None] * len(df))),
            df.get("property_type", pd.Series([None] * len(df))),
        )
    ]
    unmapped = df["property_type_clean"].isna()
    stats.dropped_not_residential += int(unmapped.sum())
    df = df[~unmapped]

    # 2. Numeric coercion + placeholder-artifact filtering.
    df["actual_worth"] = pd.to_numeric(df.get("actual_worth"), errors="coerce")
    df["procedure_area"] = pd.to_numeric(df.get("procedure_area"), errors="coerce")

    placeholder = (
        df["actual_worth"].isna()
        | df["procedure_area"].isna()
        | (df["actual_worth"] <= MIN_WORTH_AED)
        | (df["procedure_area"] < MIN_SIZE_SQM)
    )
    stats.dropped_placeholder += int(placeholder.sum())
    df = df[~placeholder]

    # 3. Dates.
    df["transaction_date"] = pd.to_datetime(df.get("instance_date"), errors="coerce", dayfirst=True)
    bad_date = df["transaction_date"].isna()
    stats.dropped_unparseable_date += int(bad_date.sum())
    df = df[~bad_date]

    if df.empty:
        return df

    # 4. Derived fields per Section 7/8 schema.
    df["size_sqft"] = (df["procedure_area"] * SQM_TO_SQFT).round(2)
    df["price_aed"] = df["actual_worth"].round(2)
    df["price_per_sqft"] = (df["price_aed"] / df["size_sqft"]).round(2)
    df["bedrooms"] = df.get("rooms", pd.Series([None] * len(df))).map(parse_bedrooms)
    df["community"] = df.get("area_name", pd.Series([None] * len(df))).fillna("Unknown")
    df["property_type"] = df["property_type_clean"]

    reg_pairs = df.get("reg_type", pd.Series([None] * len(df))).map(map_registration_type)
    df["registration_type"] = [p[0] for p in reg_pairs]
    df["transaction_type"] = [p[1] for p in reg_pairs]

    df["building_name_resolved"] = df.get("building_name", pd.Series([None] * len(df))).fillna(
        df.get("project_name", pd.Series([None] * len(df)))
    )
    df["building_name_resolved"] = df["building_name_resolved"].fillna("Unregistered Building")

    df["building_id"] = [
        short_id(name, community, prefix="BLD-", width=10)
        for name, community in zip(df["building_name_resolved"], df["community"])
    ]

    raw_ids = df.get("raw_id", pd.Series(range(len(df)), index=df.index).astype(str))
    df["dedupe_key"] = [str(x) for x in raw_ids]

    intra_chunk_dup = df.duplicated(subset="dedupe_key", keep="first")
    stats.dropped_duplicate += int(intra_chunk_dup.sum())
    df = df[~intra_chunk_dup]

    cross_chunk_dup = df["dedupe_key"].isin(stats.seen_raw_ids)
    stats.dropped_duplicate += int(cross_chunk_dup.sum())
    df = df[~cross_chunk_dup]
    stats.seen_raw_ids.update(df["dedupe_key"].tolist())

    df["transaction_id"] = [
        short_id(rid, str(idx), prefix="TXN-", width=15)
        for rid, idx in zip(df["dedupe_key"], df.index)
    ]

    df["buyer_type"] = None  # not present at row level in the DLD open dataset
    # Provenance (Phase D: "full DLD or portal data partnership"): this
    # adapter's default caller (this file's own CLI) reads a Kaggle mirror
    # of DLD's own open dataset, real transaction data but not a licensed
    # partnership feed, tagged "dld_kaggle". scripts/ingest_dld_open_api.py
    # (Phase 12b) reuses this same cleaning pipeline for rows fetched
    # directly from Dubai Pulse's official API instead, passing
    # provenance="dld_open_free" -- same underlying open dataset, distinct
    # tag because "we called the government's own API" is a stronger
    # provenance claim than "we downloaded a third-party CSV mirror of it".
    df["data_provenance"] = provenance

    return df[
        [
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
    ]


def upsert_buildings(session, df: pd.DataFrame, stats: LoadStats) -> None:
    from sqlalchemy.dialects import postgresql, sqlite

    dialect = session.get_bind().dialect.name
    insert_fn = postgresql.insert if dialect == "postgresql" else sqlite.insert

    buildings = (
        df[["building_id", "building_name_resolved", "community"]]
        .drop_duplicates(subset=["building_id"])
        .rename(columns={"building_name_resolved": "name"})
    )
    if buildings.empty:
        return

    rows = buildings.to_dict(orient="records")
    stmt = insert_fn(Building).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["building_id"])
    session.execute(stmt)
    stats.buildings_upserted += len(rows)


def upsert_transactions(session, df: pd.DataFrame) -> None:
    from sqlalchemy.dialects import postgresql, sqlite

    if df.empty:
        return

    dialect = session.get_bind().dialect.name
    insert_fn = postgresql.insert if dialect == "postgresql" else sqlite.insert

    rows = df.drop(columns=["building_name_resolved"]).to_dict(orient="records")
    for row in rows:
        row["transaction_date"] = row["transaction_date"].date()

    stmt = insert_fn(Transaction).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["transaction_id"])
    session.execute(stmt)


def run(
    input_path: Path,
    database_url: str | None,
    chunksize: int,
    dry_run: bool,
    row_limit: int | None,
    provenance: str = "dld_kaggle",
) -> LoadStats:
    stats = LoadStats()

    with open(input_path, "r", newline="", encoding="utf-8-sig") as f:
        header = f.readline().strip().split(",")
    colmap = resolve_columns(header)

    required = {"actual_worth", "procedure_area", "instance_date"}
    missing = required - colmap.keys()
    if missing:
        raise SystemExit(
            f"Could not resolve required DLD columns {missing} in {input_path}. "
            f"Resolved so far: {colmap}. Update COLUMN_CANDIDATES to match this export."
        )
    log.info("Resolved column mapping: %s", colmap)

    engine = None
    session = None
    if not dry_run:
        engine = get_engine(database_url) if database_url else get_engine()
        Base.metadata.create_all(engine, tables=[Building.__table__, Transaction.__table__])
        from sqlalchemy.orm import Session

        session = Session(engine, future=True)

    rows_processed = 0
    reader = pd.read_csv(input_path, chunksize=chunksize, dtype=str, low_memory=False)
    for chunk in reader:
        if row_limit is not None and rows_processed >= row_limit:
            break
        if row_limit is not None:
            chunk = chunk.iloc[: max(0, row_limit - rows_processed)]

        cleaned = clean_chunk(chunk, colmap, stats, provenance)
        rows_processed += len(chunk)
        stats.rows_loaded += len(cleaned)

        if not dry_run and not cleaned.empty:
            upsert_buildings(session, cleaned, stats)
            upsert_transactions(session, cleaned)
            session.commit()

    if session is not None:
        session.close()

    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=Path("data/transactions.csv"), help="Path to the raw DLD/Kaggle CSV")
    parser.add_argument("--database-url", type=str, default=None, help="Overrides DATABASE_URL env var")
    parser.add_argument("--chunksize", type=int, default=50_000)
    parser.add_argument("--dry-run", action="store_true", help="Parse and report stats without writing to Postgres")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N raw rows (testing)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.input.exists():
        raise SystemExit(
            f"{args.input} not found. Download it first:\n"
            "  pip install kaggle --break-system-packages\n"
            "  kaggle datasets download -d alexefimik/dubai-real-estate-transactions-dataset "
            "-p ./data --unzip"
        )

    stats = run(
        input_path=args.input,
        database_url=args.database_url,
        chunksize=args.chunksize,
        dry_run=args.dry_run,
        row_limit=args.limit,
    )

    log.info("Rows read:                 %d", stats.rows_read)
    log.info("Dropped (not a sale):      %d", stats.dropped_not_sale)
    log.info("Dropped (not residential): %d", stats.dropped_not_residential)
    log.info("Dropped (placeholder):     %d", stats.dropped_placeholder)
    log.info("Dropped (bad date):        %d", stats.dropped_unparseable_date)
    log.info("Dropped (duplicate):       %d", stats.dropped_duplicate)
    log.info("Buildings upserted:        %d", stats.buildings_upserted)
    log.info("Transactions loaded:       %d%s", stats.rows_loaded, " (dry-run, not written)" if args.dry_run else "")


if __name__ == "__main__":
    main()

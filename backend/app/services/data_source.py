"""Swappable transaction data sources (Phase D: "full DLD or portal data
partnership... the exclusive or first-mover data relationship that's hard
for a competitor to replicate in a weekend, unlike the agent
orchestration").

The point of this module is narrow: make "swap in a real licensed feed"
a matter of implementing one `DataSourceProvider` and setting an env var,
not touching `comps_service.py`, the agents, or the API layer. It does
NOT create a data partnership -- `LicensedFeedDataSource` is a stub that
raises a clear "not configured" error until real credentials exist, same
posture as `STRIPE_SECRET_KEY`/`WHATSAPP_ACCESS_TOKEN` elsewhere in this
app. Nothing here has been exercised against a real licensed feed because
no such feed exists yet.

Every transaction this app has ever loaded carries a `data_provenance`
value (`synthetic` | `dld_kaggle` | `licensed_partner`) on the `transactions`
table so a consumer can always tell which kind of number it's looking at
-- see `backend/scripts/migrate_add_data_provenance.py` for bringing an
existing database up to date, and `backend/scripts/seed_db.py`'s
`--provenance` flag / `map_dld_columns.py`'s hardcoded tag for how it gets
set on load.
"""
from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from app import config

PROVENANCE_VALUES = ("synthetic", "dld_kaggle", "licensed_partner")


class DataSourceProvider(ABC):
    """A source of transaction rows shaped like the `transactions` table
    (see app/models.py's Transaction columns) plus a `data_provenance` tag."""

    provenance: str

    @abstractmethod
    def fetch_transactions(self) -> Iterator[dict]:
        """Yields dicts with the same keys scripts/seed_db.py's
        coerce_transaction() produces, `data_provenance` included."""
        raise NotImplementedError


class SyntheticDataSource(DataSourceProvider):
    """Wraps the committed synthetic seed CSV -- this repo's default and
    only real (i.e. actually loadable, no external credentials) source."""

    provenance = "synthetic"

    def __init__(self, seed_dir: Path | None = None):
        self.seed_dir = seed_dir or Path(__file__).resolve().parents[2] / "seed_data"

    def fetch_transactions(self) -> Iterator[dict]:
        path = self.seed_dir / "transactions.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} not found -- run scripts/generate_dataset.py first.")
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row["data_provenance"] = self.provenance
                yield row


class DldKaggleDataSource(DataSourceProvider):
    """Wraps a CSV already through scripts/map_dld_columns.py's cleaning
    pipeline -- real DLD/Dubai Pulse transaction data via a Kaggle mirror,
    not a licensed feed. Expects the *mapped* output shape (this class
    does not itself do DLD column renaming; see map_dld_columns.py)."""

    provenance = "dld_kaggle"

    def __init__(self, mapped_csv_path: Path):
        self.mapped_csv_path = mapped_csv_path

    def fetch_transactions(self) -> Iterator[dict]:
        if not self.mapped_csv_path.exists():
            raise FileNotFoundError(
                f"{self.mapped_csv_path} not found -- run scripts/map_dld_columns.py --input <raw DLD CSV> first."
            )
        with open(self.mapped_csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row["data_provenance"] = self.provenance
                yield row


class LicensedFeedDataSource(DataSourceProvider):
    """Stub for a real licensed data partnership (DLD's official channel,
    Bayut/Property Finder/PropertyMonitor/Reidin, or a brokerage
    data-sharing agreement -- see the MVP roadmap's risk #1). No such
    partnership exists yet, so this raises rather than silently returning
    nothing or fabricating rows -- a caller that reaches this class with
    it unconfigured has a bug, not a degraded-but-working feature."""

    provenance = "licensed_partner"

    def __init__(self, feed_url: str | None = None, api_key: str | None = None):
        self.feed_url = feed_url or config.LICENSED_DATA_FEED_URL
        self.api_key = api_key or config.LICENSED_DATA_FEED_API_KEY

    def fetch_transactions(self) -> Iterator[dict]:
        if not self.feed_url:
            raise RuntimeError(
                "No licensed data partnership is configured (LICENSED_DATA_FEED_URL unset). "
                "This is expected until a real data partnership exists -- see README 'Data partnership'."
            )
        import httpx

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with httpx.Client(timeout=30) as client:
            res = client.get(self.feed_url, headers=headers)
            res.raise_for_status()
            for row in res.json():
                row["data_provenance"] = self.provenance
                yield row


def get_data_source(name: str | None = None, **kwargs) -> DataSourceProvider:
    """Factory keyed by name (defaults to $DATA_SOURCE, then "synthetic").
    This is the one place a caller should construct a provider from, so
    swapping the active source is a config change here, not a hunt
    through every place that touches transaction data."""
    name = name or config.DATA_SOURCE
    if name == "synthetic":
        return SyntheticDataSource(**kwargs)
    if name == "dld_kaggle":
        if "mapped_csv_path" not in kwargs:
            raise ValueError("dld_kaggle requires mapped_csv_path=<Path to map_dld_columns.py's output>")
        return DldKaggleDataSource(**kwargs)
    if name == "licensed_partner":
        return LicensedFeedDataSource(**kwargs)
    raise ValueError(f"Unknown data source {name!r}; expected one of {PROVENANCE_VALUES}")

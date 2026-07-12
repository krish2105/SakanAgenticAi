"""Tests for app/services/data_source.py.

LicensedFeedDataSource has never round-tripped against a real licensed
feed -- no such feed exists. Its tests only cover: it refuses to run
unconfigured, and its HTTP call shape is correct against a monkeypatched
httpx client.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.services.data_source import (
    DldKaggleDataSource,
    LicensedFeedDataSource,
    SyntheticDataSource,
    get_data_source,
)

SEED_DIR = Path(__file__).resolve().parents[1] / "seed_data"


def test_synthetic_data_source_yields_real_seed_rows_tagged_synthetic():
    source = SyntheticDataSource(seed_dir=SEED_DIR)
    rows = list(source.fetch_transactions())
    assert len(rows) == 600
    assert all(r["data_provenance"] == "synthetic" for r in rows)
    assert all("transaction_id" in r and "price_aed" in r for r in rows)


def test_synthetic_data_source_raises_clearly_when_csv_missing(tmp_path):
    source = SyntheticDataSource(seed_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="generate_dataset.py"):
        list(source.fetch_transactions())


def test_dld_kaggle_data_source_tags_provenance(tmp_path):
    csv_path = tmp_path / "mapped.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["transaction_id", "building_id", "community", "property_type", "bedrooms", "price_aed"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "transaction_id": "TXN-DLD-001",
                "building_id": "BLD-DLD-001",
                "community": "Business Bay",
                "property_type": "Apartment",
                "bedrooms": "2",
                "price_aed": "1500000",
            }
        )

    source = DldKaggleDataSource(mapped_csv_path=csv_path)
    rows = list(source.fetch_transactions())
    assert len(rows) == 1
    assert rows[0]["data_provenance"] == "dld_kaggle"
    assert rows[0]["transaction_id"] == "TXN-DLD-001"


def test_dld_kaggle_data_source_raises_clearly_when_csv_missing(tmp_path):
    source = DldKaggleDataSource(mapped_csv_path=tmp_path / "missing.csv")
    with pytest.raises(FileNotFoundError, match="map_dld_columns.py"):
        list(source.fetch_transactions())


def test_licensed_feed_data_source_raises_without_configuration():
    source = LicensedFeedDataSource(feed_url=None, api_key=None)
    with pytest.raises(RuntimeError, match="not configured|LICENSED_DATA_FEED_URL"):
        list(source.fetch_transactions())


def test_licensed_feed_data_source_calls_configured_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"transaction_id": "TXN-LIC-001", "price_aed": 2000000}]

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            calls.append((url, headers))
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)

    source = LicensedFeedDataSource(feed_url="https://example.com/feed", api_key="secret-key")
    rows = list(source.fetch_transactions())

    assert len(calls) == 1
    assert calls[0][0] == "https://example.com/feed"
    assert calls[0][1] == {"Authorization": "Bearer secret-key"}
    assert rows == [{"transaction_id": "TXN-LIC-001", "price_aed": 2000000, "data_provenance": "licensed_partner"}]


def test_get_data_source_factory_dispatches_by_name():
    assert isinstance(get_data_source("synthetic", seed_dir=SEED_DIR), SyntheticDataSource)
    assert isinstance(get_data_source("licensed_partner"), LicensedFeedDataSource)

    with pytest.raises(ValueError, match="mapped_csv_path"):
        get_data_source("dld_kaggle")

    with pytest.raises(ValueError, match="Unknown data source"):
        get_data_source("carrier_pigeon")


def test_get_data_source_defaults_to_config_data_source(monkeypatch):
    import app.services.data_source as data_source_module

    monkeypatch.setattr(data_source_module.config, "DATA_SOURCE", "synthetic")
    source = get_data_source(seed_dir=SEED_DIR)
    assert isinstance(source, SyntheticDataSource)

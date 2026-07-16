"""Real DLD-derived transaction data via RapidAPI's "UAE Real Estate Data
API". Fully mocked at the HTTP layer (no live account exists to test
against from this sandbox) -- this covers our own wiring (response-shape
parsing, filtering, field mapping, pagination, dedup), not the vendor's
actual API behavior. The mock response shape mirrors a real captured
example (see the script's docstring) including its double-nested
data.data.attributes envelope."""
from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import scripts.ingest_bayut_transactions as ingest_module
from app.models import Transaction

API_HOST = ingest_module.API_HOST


def _make_transaction(**overrides) -> dict:
    row = {
        "id": "2140214fd198b7366f7ff0f0aaf41e98",
        "bedrooms": 2,
        "contract_end_date": "",
        "contract_start_date": "",
        "high_level_location_name": "Dubai Marina",
        "location_id": 11873,
        "location_name": "Marina Shores",
        "location_slug": "dubai-marina-marina-shores",
        "price": 3219888,
        "price_per_sqft": 2635.8064424020477,
        "property_number": "1902",
        "property_size": 1221.59501099999999,
        "property_type": "Apartment",
        "status": "Off-plan",
        "transaction_date": "2026-07-14",
    }
    row.update(overrides)
    return row


def _page_payload(transactions: list[dict], page: int, total_pages: int, total_items: int) -> dict:
    # Mirrors the real captured shape: root.data.data.attributes.{...}
    return {
        "success": True,
        "data": {
            "data": {
                "attributes": {
                    "page": page,
                    "summary": {"sale_avg_price_per_sqft": 2500},
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "transactions": transactions,
                }
            }
        },
    }


def _install_mock_transport(monkeypatch, pages_by_location: dict[int, list[list[dict]]]):
    """pages_by_location: {location_id: [page1_rows, page2_rows, ...]}"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-rapidapi-host"] == API_HOST
        assert request.headers["x-rapidapi-key"] == "fake-key"
        location_id = int(request.url.params["location_id"])
        page = int(request.url.params["page"])
        pages = pages_by_location[location_id]
        rows = pages[page - 1]
        total_pages = len(pages)
        total_items = sum(len(p) for p in pages)
        return httpx.Response(200, json=_page_payload(rows, page, total_pages, total_items))

    transport = httpx.MockTransport(handler)

    class _PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)


def _write_location_ids(tmp_path, monkeypatch, mapping: dict[str, int]):
    path = tmp_path / "bayut_location_ids.json"
    path.write_text(json.dumps(mapping))
    monkeypatch.setattr(ingest_module, "LOCATION_IDS_PATH", path)
    return path


def test_find_attributes_handles_double_nested_envelope():
    payload = _page_payload([_make_transaction()], page=1, total_pages=1, total_items=1)
    found = ingest_module._find_attributes(payload)
    assert found is not None
    assert found["total_items"] == 1
    assert len(found["transactions"]) == 1


def test_find_attributes_returns_none_for_unrelated_payload():
    assert ingest_module._find_attributes({"success": False, "error": "nope"}) is None


def test_status_to_reg_type_off_plan_and_ready():
    assert ingest_module._status_to_reg_type("Off-plan") == ("Oqood", "Off-Plan")
    assert ingest_module._status_to_reg_type("Ready") == ("Title Deed", "Sale")
    assert ingest_module._status_to_reg_type(None) == ("Title Deed", "Sale")


def test_clean_row_maps_a_realistic_transaction():
    stats = ingest_module.IngestStats()
    row = _make_transaction()
    row["_community"] = "Dubai Marina"

    cleaned = ingest_module.clean_row(row, stats)

    assert cleaned is not None
    assert cleaned["community"] == "Dubai Marina"
    assert cleaned["property_type"] == "Apartment"
    assert cleaned["bedrooms"] == 2
    assert cleaned["price_aed"] == 3219888.0
    assert cleaned["registration_type"] == "Oqood"
    assert cleaned["transaction_type"] == "Off-Plan"
    assert cleaned["data_provenance"] == "dld_bayut"
    assert cleaned["transaction_id"].startswith("TXN-")
    assert cleaned["building_id"].startswith("BLD-")


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"price": None}, "missing price"),
        ({"property_size": 0}, "zero size"),
        ({"price": 500}, "below MIN_PRICE_AED"),
        ({"price_per_sqft": 120, "price": 146_400, "property_size": 1220}, "rental-shaped price/sqft"),
        ({"transaction_date": "not-a-date"}, "unparseable date"),
        ({"property_type": "Compound"}, "unmappable property type"),
    ],
)
def test_clean_row_drops_bad_rows(overrides, reason):
    stats = ingest_module.IngestStats()
    row = _make_transaction(**overrides)
    row["_community"] = "Dubai Marina"

    assert ingest_module.clean_row(row, stats) is None, reason


def test_clean_row_dedupes_repeated_ids():
    stats = ingest_module.IngestStats()
    row = _make_transaction()
    row["_community"] = "Dubai Marina"

    first = ingest_module.clean_row(dict(row), stats)
    second = ingest_module.clean_row(dict(row), stats)

    assert first is not None
    assert second is None
    assert stats.dropped_duplicate == 1


def test_missing_api_key_raises_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest_module.config, "RAPIDAPI_KEY", None)
    _write_location_ids(tmp_path, monkeypatch, {"Dubai Marina": 11873})

    with pytest.raises(SystemExit, match="RAPIDAPI_KEY"):
        ingest_module.run(database_url=None, dry_run=True, max_requests=10)


def test_missing_location_ids_file_raises_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(ingest_module.config, "RAPIDAPI_KEY", "fake-key")
    monkeypatch.setattr(ingest_module, "LOCATION_IDS_PATH", tmp_path / "does_not_exist.json")

    with pytest.raises(SystemExit, match="resolve_bayut_locations"):
        ingest_module.run(database_url=None, dry_run=True, max_requests=10)


def test_run_end_to_end_paginates_filters_and_loads(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_module.config, "RAPIDAPI_KEY", "fake-key")
    _write_location_ids(tmp_path, monkeypatch, {"Dubai Marina": 11873})

    good_row_1 = _make_transaction(id="txn-1", property_number="101")
    good_row_2 = _make_transaction(id="txn-2", property_number="102", status="Ready")
    bad_row = _make_transaction(id="txn-3", property_number="103", price=200)  # placeholder, dropped

    _install_mock_transport(
        monkeypatch,
        {11873: [[good_row_1, bad_row], [good_row_2]]},  # two pages
    )

    db_path = tmp_path / "bayut_test.db"
    database_url = f"sqlite:///{db_path}"

    stats = ingest_module.run(database_url=database_url, dry_run=False, max_requests=10)

    assert stats.requests_made == 2  # one per page
    assert stats.rows_fetched == 3
    assert stats.dropped_placeholder == 1
    assert stats.rows_loaded == 2

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        transactions = session.scalars(select(Transaction)).all()
        assert len(transactions) == 2
        assert all(t.data_provenance == "dld_bayut" for t in transactions)
        types = {t.transaction_type for t in transactions}
        assert types == {"Off-Plan", "Sale"}


def test_run_respects_max_requests_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_module.config, "RAPIDAPI_KEY", "fake-key")
    _write_location_ids(
        tmp_path, monkeypatch, {"Dubai Marina": 11873, "Downtown Dubai": 22000}
    )

    row_a = _make_transaction(id="a")
    row_b = _make_transaction(id="b")
    _install_mock_transport(monkeypatch, {11873: [[row_a]], 22000: [[row_b]]})

    stats = ingest_module.run(database_url=None, dry_run=True, max_requests=1)

    assert stats.requests_made == 1  # stopped after the first community's one page
    assert stats.rows_loaded == 1

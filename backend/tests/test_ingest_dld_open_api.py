"""Phase 12b -- Dubai Pulse open-data API ingestion. Fully mocked at the
HTTP layer (no live account exists to test against from this sandbox, same
posture as LicensedFeedDataSource's own test) -- this covers our own
wiring (OAuth token exchange, pagination, delegating to
map_dld_columns.run() with provenance="dld_open_free"), not Dubai Pulse's
actual API behavior."""
from __future__ import annotations

import csv
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import scripts.ingest_dld_open_api as ingest_module
from app.models import Transaction

FIXTURE = Path(__file__).parent / "fixtures" / "dld_transactions_sample.csv"


def _fixture_rows() -> list[dict]:
    with open(FIXTURE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _install_mock_transport(monkeypatch, rows: list[dict], page_size: int = 1000):
    """Routes every httpx call in this module through a fake transport: the
    OAuth endpoint returns a fake token, the transactions endpoint paginates
    `rows` by offset/limit exactly like the real function expects."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/client_credential/accesstoken":
            return httpx.Response(200, json={"access_token": "fake-token"})
        if request.url.path == "/open/dld/dld_transactions-open-api":
            offset = int(request.url.params.get("offset", "0"))
            limit = int(request.url.params.get("limit", str(page_size)))
            return httpx.Response(200, json=rows[offset : offset + limit])
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)

    class _PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)

    real_post = httpx.post

    def patched_post(url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.post(url, **{k: v for k, v in kwargs.items() if k != "timeout"})

    monkeypatch.setattr(httpx, "post", patched_post)
    return real_post


def test_missing_credentials_raises_clear_error(monkeypatch):
    monkeypatch.setattr(ingest_module.config, "DLD_OPEN_DATA_API_KEY", None)
    monkeypatch.setattr(ingest_module.config, "DLD_OPEN_DATA_API_SECRET", None)

    try:
        ingest_module.run(database_url=None, dry_run=True, row_limit=None)
        raised = False
    except SystemExit as exc:
        raised = True
        assert "DLD_OPEN_DATA_API_KEY" in str(exc)
    assert raised


def test_ingest_fetches_paginates_and_loads_with_open_free_provenance(tmp_path, monkeypatch):
    rows = _fixture_rows()
    _install_mock_transport(monkeypatch, rows, page_size=5)  # forces multiple pages over 12 rows

    db_path = tmp_path / "dld_open_test.db"
    database_url = f"sqlite:///{db_path}"

    stats = ingest_module.run(
        database_url=database_url,
        dry_run=False,
        row_limit=None,
        api_key="fake-key",
        api_secret="fake-secret",
    )

    assert stats.rows_read == 12  # every fixture row round-tripped through pagination
    assert stats.rows_loaded == 4  # same cleaning outcome as map_dld_columns' own test

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        transactions = session.scalars(select(Transaction)).all()
        assert len(transactions) == 4
        assert all(t.data_provenance == "dld_open_free" for t in transactions)


def test_ingest_respects_row_limit(monkeypatch):
    rows = _fixture_rows()
    _install_mock_transport(monkeypatch, rows, page_size=5)

    stats = ingest_module.run(
        database_url=None, dry_run=True, row_limit=3, api_key="fake-key", api_secret="fake-secret"
    )

    assert stats.rows_read == 3


def test_ingest_handles_empty_response(monkeypatch, caplog):
    _install_mock_transport(monkeypatch, rows=[])

    with caplog.at_level("WARNING"):
        result = ingest_module.run(
            database_url=None, dry_run=True, row_limit=None, api_key="fake-key", api_secret="fake-secret"
        )

    assert result is None
    assert "no rows" in caplog.text.lower()

"""Phase 2 -- observability: health/readiness endpoints, request-id
propagation, structured logging, and the global exception handler.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter, configure_logging, request_id_ctx
from app.main import app


def test_healthz_is_static_and_does_not_touch_dependencies():
    with TestClient(app) as client:
        res = client.get("/healthz")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        # legacy alias still works (render.yaml points here)
        assert client.get("/health").status_code == 200


def test_readyz_reports_database_ok(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/readyz")
        assert res.status_code == 200
        body = res.json()
        assert body["ready"] is True
        assert body["checks"]["database"]["ok"] is True
        # Redis/Qdrant are skipped (unset / embeddings off), not failing.
        assert body["checks"]["redis"]["ok"] is True
        assert body["checks"]["qdrant"]["ok"] is True


def test_response_carries_request_id_header():
    with TestClient(app) as client:
        res = client.get("/healthz")
        assert res.headers.get("X-Request-ID")


def test_inbound_request_id_is_preserved():
    with TestClient(app) as client:
        res = client.get("/healthz", headers={"X-Request-ID": "trace-abc-123"})
        assert res.headers.get("X-Request-ID") == "trace-abc-123"


def test_global_exception_handler_returns_clean_500():
    # Mount a route that raises, on the real app, to exercise the handler.
    boom = APIRouter()

    @boom.get("/_test_boom")
    async def _boom():
        raise RuntimeError("kaboom")

    app.include_router(boom)
    try:
        # raise_server_exceptions=False so TestClient returns the 500 response
        # the handler produced instead of re-raising into the test.
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/_test_boom")
            assert res.status_code == 500
            assert res.json() == {"detail": "Internal server error"}
            assert res.headers.get("X-Request-ID")
    finally:
        app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/_test_boom"]


def test_json_formatter_emits_request_id_and_valid_json():
    configure_logging()
    formatter = JsonFormatter()
    token = request_id_ctx.set("req-xyz")
    try:
        record = logging.LogRecord(
            name="sakan.test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="hello %s", args=("world",), exc_info=None,
        )
        record.request_id = request_id_ctx.get()
        line = formatter.format(record)
        parsed = json.loads(line)
        assert parsed["msg"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["request_id"] == "req-xyz"
    finally:
        request_id_ctx.reset(token)

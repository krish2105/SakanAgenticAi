"""Optional error tracking (Sentry) + dependency readiness checks.

Both are free-tier friendly and fully optional: Sentry only initializes when
SENTRY_DSN is set, and readiness reports each dependency's state without adding
any hard runtime dependency.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import text

from app import config
from app.db import get_engine

log = logging.getLogger("sakan.observability")


def init_sentry() -> bool:
    """Initialize Sentry if SENTRY_DSN is set (and the SDK is installed).
    Returns True if enabled. No-op otherwise -- keeps the free/default path
    dependency-free."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=config.SAKAN_ENV,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            send_default_pii=False,
        )
        log.info("Sentry error tracking enabled (env=%s).", config.SAKAN_ENV)
        return True
    except Exception:  # noqa: BLE001
        log.exception("SENTRY_DSN is set but Sentry failed to initialize; continuing without it.")
        return False


def _check_database() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"error: {exc}"


def _check_redis() -> tuple[bool, str]:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return True, "skipped (REDIS_URL unset; in-memory pub/sub)"
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"error: {exc}"


def _check_qdrant() -> tuple[bool, str]:
    if not config.ENABLE_SEMANTIC_EMBEDDINGS:
        return True, "skipped (ENABLE_SEMANTIC_EMBEDDINGS off)"
    qdrant_url = config.QDRANT_URL
    if not qdrant_url:
        return True, "skipped (QDRANT_URL unset)"
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=qdrant_url, api_key=config.QDRANT_API_KEY, timeout=3)
        client.get_collections()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"error: {exc}"


def check_readiness() -> tuple[bool, dict]:
    """Readiness = can we serve real traffic. The database is the only hard
    dependency (a down Qdrant/Redis degrades to documented fallbacks, it doesn't
    make the service unable to serve). Returns (overall_ok, per-check detail).
    """
    db_ok, db_detail = _check_database()
    redis_ok, redis_detail = _check_redis()
    qdrant_ok, qdrant_detail = _check_qdrant()

    checks = {
        "database": {"ok": db_ok, "detail": db_detail},
        "redis": {"ok": redis_ok, "detail": redis_detail},
        "qdrant": {"ok": qdrant_ok, "detail": qdrant_detail},
    }
    # Only the database gates readiness.
    return db_ok, checks

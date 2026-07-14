from pathlib import Path

import pytest

SEED_DIR = Path(__file__).resolve().parents[1] / "seed_data"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The shared slowapi limiter is a module-level singleton; without a reset
    between tests its per-IP counters bleed across tests (every TestClient looks
    like the same 'testclient' host), causing spurious 429s once total
    login/query calls in a minute exceed a limit. Reset before and after each
    test so limits are exercised only within the test that intends to."""
    from app.ratelimit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def _reset_cache():
    """app.cache's in-memory fallback is a module-level dict; without a reset
    between tests, a cached response from one test's seeded_sqlite_db (e.g.
    GET /comps with a given set of params) would leak into a later test that
    happens to call the same endpoint with the same params against a
    different (fresh) fixture DB, returning stale data instead of a live
    query."""
    from app.cache import _memory_cache

    _memory_cache.clear()
    yield
    _memory_cache.clear()


@pytest.fixture()
def seeded_sqlite_db(tmp_path, monkeypatch):
    """Points app.db at a fresh SQLite DB seeded with the synthetic dataset,
    so agent nodes that hit the DB (comps_agent) are exercised end-to-end
    without needing a running Postgres instance."""
    db_path = tmp_path / "sakan_agents_test.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from scripts.seed_db import run as seed_run

    seed_run(SEED_DIR, database_url)
    return database_url

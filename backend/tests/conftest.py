import os
from pathlib import Path

import pytest

SEED_DIR = Path(__file__).resolve().parents[1] / "seed_data"


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

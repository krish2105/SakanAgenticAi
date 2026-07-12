"""Phase 1 -- Alembic migrations.

Guards two things:
  1. Applying all migrations to a fresh DB reproduces exactly app.models
     (no drift between the models and the migration history).
  2. scripts/run_migrations.py adopts a pre-Alembic ("legacy") database by
     stamping the baseline rather than erroring on already-existing tables.
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    # env.py reads the URL from app.db.get_engine(), which honors DATABASE_URL.
    return cfg


def test_migrations_match_models(tmp_path, monkeypatch):
    db_path = tmp_path / "mig_sync.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"compare_type": True, "target_metadata": Base.metadata}
        )
        diff = compare_metadata(ctx, Base.metadata)

    assert diff == [], (
        "Models and migrations are out of sync -- run "
        "`alembic revision --autogenerate` and commit the result. Diff:\n"
        f"{diff}"
    )


def test_run_migrations_adopts_legacy_database(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    # Simulate the *actual* pre-Alembic live DB: the original baseline schema
    # (no Phase 3 auth_tokens table / user security columns) and no
    # alembic_version. Build it by running the baseline migration, then dropping
    # alembic_version to mimic "was never Alembic-managed".
    command.upgrade(_alembic_config(database_url), "0001_baseline")
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE alembic_version")
    insp = inspect(engine)
    assert "alembic_version" not in insp.get_table_names()
    assert "auth_tokens" not in insp.get_table_names()  # legacy: pre-Phase-3

    # Must adopt (stamp baseline) then upgrade forward -- not error on existing
    # tables, and it should add the Phase 3 schema.
    from scripts.run_migrations import main as run_migrations

    run_migrations()

    insp2 = inspect(create_engine(database_url))
    tables = insp2.get_table_names()
    assert "alembic_version" in tables
    assert "auth_tokens" in tables  # Phase 3 applied on top of the adopted baseline
    user_cols = {c["name"] for c in insp2.get_columns("users")}
    assert {"email_verified", "failed_login_attempts", "locked_until"} <= user_cols


def test_run_migrations_creates_fresh_database(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from scripts.run_migrations import main as run_migrations

    run_migrations()

    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert {"users", "deal_queries", "audit_log", "transactions", "alembic_version"} <= tables

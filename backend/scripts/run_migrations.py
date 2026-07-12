#!/usr/bin/env python3
"""Deploy-time database migration bootstrap.

Runs at container start (docker-entrypoint.sh) before uvicorn. Handles the
three states a Sakan AI database can be in, so a single command is safe whether
the DB is brand new, was created by the old pre-Alembic create_all path, or is
already Alembic-managed:

  1. Alembic-managed (has `alembic_version`)  -> upgrade to head.
  2. Legacy (has app tables, no `alembic_version`, e.g. the currently-live DB
     built by create_all + the old migrate_*.py scripts) -> stamp the baseline
     (adopt the existing schema without re-creating it), then upgrade to head.
  3. Fresh (no tables) -> upgrade to head (baseline creates everything).

Idempotent: safe to run on every deploy.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from app.db import get_engine  # noqa: E402

log = logging.getLogger("sakan.migrations")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASELINE_REVISION = "0001_baseline"
# A table that only ever existed under the legacy create_all path -- its
# presence (without alembic_version) means "adopt, don't re-create".
LEGACY_MARKER_TABLE = "users"


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def main() -> None:
    engine = get_engine()
    tables = set(inspect(engine).get_table_names())
    cfg = _alembic_config()

    if "alembic_version" in tables:
        log.info("Alembic-managed database detected; upgrading to head.")
        command.upgrade(cfg, "head")
    elif LEGACY_MARKER_TABLE in tables:
        log.info(
            "Legacy pre-Alembic schema detected (found %r, no alembic_version); "
            "stamping baseline %s then upgrading to head.",
            LEGACY_MARKER_TABLE,
            BASELINE_REVISION,
        )
        command.stamp(cfg, BASELINE_REVISION)
        command.upgrade(cfg, "head")
    else:
        log.info("Fresh database detected; running all migrations to head.")
        command.upgrade(cfg, "head")

    log.info("Database migrations complete.")


if __name__ == "__main__":
    main()

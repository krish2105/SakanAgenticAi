"""baseline schema (all tables as of app.models)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-13

The baseline is created directly from the app's SQLAlchemy metadata via
create_all, so it is guaranteed to match app/models.py exactly (no risk of the
migration drifting from the models it's supposed to represent). This folds in
what the old hand-rolled scripts/migrate_add_data_provenance.py and
migrate_billing_columns.py did -- those columns are part of the models now, so
they're part of the baseline. Subsequent migrations use explicit op.* calls.

A database that predates Alembic (schema built by the old create_all path) is
adopted at this revision via `alembic stamp` -- see scripts/run_migrations.py.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from app.models import Base

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

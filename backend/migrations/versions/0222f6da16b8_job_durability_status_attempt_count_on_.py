"""job durability: status + attempt_count on deal_queries

Revision ID: 0222f6da16b8
Revises: 0db51d8889f2
Create Date: 2026-07-14

Phase 4: a persisted, authoritative job-status column (pending -> running ->
done|failed) plus an attempt counter, so a lost pipeline run (instance
restart mid-run) is detectable and retryable via POST /deals/{id}/retry,
instead of only being inferable (unreliably) from deal_state/agent_trace.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0222f6da16b8"
down_revision: Union[str, None] = "0db51d8889f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("deal_queries", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'"))
        )
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0"))
        )


def downgrade() -> None:
    with op.batch_alter_table("deal_queries", schema=None) as batch_op:
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("status")

"""baseline schema (original 7 tables, pre auth-hardening)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-13

Explicit, frozen DDL for the schema as it stood before Phase 3. It is written
out (rather than create_all from live metadata) so that autogenerate against a
DB at this revision correctly detects later model changes as diffs -- a
create_all baseline always reflects *current* models, which makes every
subsequent autogenerate come back empty and would double-create tables on a
fresh DB.

A database that predates Alembic (built by the old create_all path) is adopted
at this revision via `alembic stamp` -- see scripts/run_migrations.py.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSONB on Postgres, plain JSON elsewhere (SQLite in tests) -- mirrors
# app.models.JSONType.
JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "developers",
        sa.Column("developer_id", sa.String(length=10), primary_key=True),
        sa.Column("name", sa.String(length=100)),
        sa.Column("track_record_score", sa.Integer()),
        sa.Column("active_projects_count", sa.Integer()),
        sa.Column("delivery_delay_rate", sa.Numeric(4, 2)),
    )
    op.create_table(
        "buildings",
        sa.Column("building_id", sa.String(length=10), primary_key=True),
        sa.Column("name", sa.String(length=150)),
        sa.Column("community", sa.String(length=100)),
        sa.Column("developer_id", sa.String(length=10), sa.ForeignKey("developers.developer_id")),
        sa.Column("completion_status", sa.String(length=20)),
        sa.Column("total_units", sa.Integer()),
        sa.Column("avg_price_per_sqft", sa.Numeric(10, 2)),
    )
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(length=15), primary_key=True),
        sa.Column("building_id", sa.String(length=10), sa.ForeignKey("buildings.building_id")),
        sa.Column("community", sa.String(length=100)),
        sa.Column("property_type", sa.String(length=20)),
        sa.Column("bedrooms", sa.Integer()),
        sa.Column("size_sqft", sa.Numeric(8, 2)),
        sa.Column("price_aed", sa.Numeric(12, 2)),
        sa.Column("price_per_sqft", sa.Numeric(10, 2)),
        sa.Column("transaction_type", sa.String(length=20)),
        sa.Column("transaction_date", sa.Date()),
        sa.Column("registration_type", sa.String(length=20)),
        sa.Column("buyer_type", sa.String(length=20)),
        sa.Column("data_provenance", sa.String(length=20), nullable=False),
    )
    op.create_table(
        "off_plan_projects",
        sa.Column("project_id", sa.String(length=10), primary_key=True),
        sa.Column("name", sa.String(length=150)),
        sa.Column("developer_id", sa.String(length=10), sa.ForeignKey("developers.developer_id")),
        sa.Column("community", sa.String(length=100)),
        sa.Column("launch_date", sa.Date()),
        sa.Column("handover_date", sa.Date()),
        sa.Column("payment_plan_structure", sa.Text()),
        sa.Column("escrow_account_status", sa.String(length=20)),
        sa.Column("rera_registration_number", sa.String(length=30)),
        sa.Column("percent_sold", sa.Numeric(5, 2)),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("role", sa.String(length=20)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255)),
        sa.Column("stripe_subscription_id", sa.String(length=255)),
        sa.Column("subscription_status", sa.String(length=30)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"])
    op.create_table(
        "deal_queries",
        sa.Column("query_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("raw_query", sa.Text()),
        sa.Column("query_type", sa.String(length=20)),
        sa.Column("deal_state", JSONType),
        sa.Column("agent_trace", JSONType),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("deal_queries.query_id")),
        sa.Column("event_type", sa.String(length=50)),
        sa.Column("event_payload", JSONType),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("deal_queries")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("off_plan_projects")
    op.drop_table("transactions")
    op.drop_table("buildings")
    op.drop_table("developers")

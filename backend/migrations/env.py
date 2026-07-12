"""Alembic environment for Sakan AI.

The DB URL comes from the app's own `app.db.get_engine()` (which reads
DATABASE_URL and normalizes postgres:// -> postgresql+psycopg2://), so
alembic and the app never disagree about which database or driver to use.
`target_metadata` is the app's `Base.metadata`, enabling autogenerate and the
models-vs-migrations sync check in tests/test_migrations.py.
"""
from __future__ import annotations

from alembic import context

from app.db import get_engine
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    engine = get_engine()
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://sakan:sakan@localhost:5432/sakan"
)


def _normalize_url(url: str) -> str:
    """Managed Postgres providers (Neon, Supabase, Render) hand out plain
    postgresql:// connection strings; SQLAlchemy needs the driver named
    explicitly. Rewriting it here means a copy-pasted connection string
    just works instead of silently needing manual editing."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


def get_engine(database_url: str | None = None):
    url = database_url or os.environ.get("DATABASE_URL", DATABASE_URL)
    normalized = _normalize_url(url)
    # connect_timeout: psycopg2 has no default, so a stalled TCP handshake
    # (a suspended free-tier Postgres taking unusually long to wake, a
    # network blip that silently drops packets instead of rejecting) hangs
    # the calling thread indefinitely instead of raising -- which the deal
    # pipeline can't recover from or report. pool_pre_ping avoids handing
    # out a connection that went stale while idle.
    connect_args = {"connect_timeout": 10} if normalized.startswith("postgresql") else {}
    return create_engine(normalized, future=True, pool_pre_ping=True, connect_args=connect_args)


def get_session_factory(engine=None):
    engine = engine or get_engine()
    return sessionmaker(bind=engine, future=True)

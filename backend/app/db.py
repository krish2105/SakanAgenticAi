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
    return create_engine(_normalize_url(url), future=True)


def get_session_factory(engine=None):
    engine = engine or get_engine()
    return sessionmaker(bind=engine, future=True)

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://sakan:sakan@localhost:5432/sakan"
)


def get_engine(database_url: str | None = None):
    return create_engine(database_url or os.environ.get("DATABASE_URL", DATABASE_URL), future=True)


def get_session_factory(engine=None):
    engine = engine or get_engine()
    return sessionmaker(bind=engine, future=True)

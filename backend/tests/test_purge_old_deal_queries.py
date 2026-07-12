from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import get_engine, get_session_factory
from app.models import AuditLog, Base, DealQuery, User
from scripts.purge_old_deal_queries import purge


def _make_user(session) -> int:
    user = User(email="purge-test@example.com", hashed_password="x", full_name=None, role="Agent")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.user_id


def test_purge_deletes_only_rows_older_than_the_retention_window(seeded_sqlite_db):
    engine = get_engine()
    Base.metadata.create_all(engine, tables=[User.__table__, DealQuery.__table__, AuditLog.__table__])
    session_factory = get_session_factory(engine)

    now = datetime.now(timezone.utc)
    with session_factory() as session:
        owner_id = _make_user(session)

        old = DealQuery(owner_id=owner_id, raw_query="old query", deal_state=None, agent_trace=[])
        recent = DealQuery(owner_id=owner_id, raw_query="recent query", deal_state=None, agent_trace=[])
        session.add_all([old, recent])
        session.commit()
        session.refresh(old)
        session.refresh(recent)

        # created_at has a server_default of now(); backdate the "old" row directly.
        session.query(DealQuery).filter_by(query_id=old.query_id).update(
            {"created_at": now - timedelta(days=200)}
        )
        session.add(AuditLog(query_id=old.query_id, event_type="agent:query", event_payload={"a": 1}))
        session.add(AuditLog(query_id=recent.query_id, event_type="agent:query", event_payload={"a": 2}))
        session.commit()

        old_id, recent_id = old.query_id, recent.query_id

    # Dry run must not delete anything.
    dry_run_count = purge(retention_days=180, dry_run=True)
    assert dry_run_count == 1

    with session_factory() as session:
        assert session.get(DealQuery, old_id) is not None

    deleted_count = purge(retention_days=180, dry_run=False)
    assert deleted_count == 1

    with session_factory() as session:
        assert session.get(DealQuery, old_id) is None
        assert session.get(DealQuery, recent_id) is not None
        assert session.scalars(select(AuditLog).where(AuditLog.query_id == old_id)).first() is None
        assert session.scalars(select(AuditLog).where(AuditLog.query_id == recent_id)).first() is not None


def test_purge_is_a_noop_when_nothing_is_expired(seeded_sqlite_db):
    engine = get_engine()
    Base.metadata.create_all(engine, tables=[User.__table__, DealQuery.__table__, AuditLog.__table__])
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        owner_id = _make_user(session)
        session.add(DealQuery(owner_id=owner_id, raw_query="brand new", deal_state=None, agent_trace=[]))
        session.commit()

    assert purge(retention_days=180, dry_run=False) == 0

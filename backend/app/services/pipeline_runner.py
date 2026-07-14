"""Runs the LangGraph deal pipeline in a worker thread, streaming state
snapshots to any WS subscribers and persisting the result to Postgres."""
from __future__ import annotations

import asyncio
import logging
import secrets

from app import config
from app.agents.graph import get_deal_pipeline
from app.db import get_engine, get_session_factory
from app.deal_state import DealState
from app.models import AuditLog, Base, DealQuery, User
from app.streaming import publish_threadsafe

log = logging.getLogger("sakan.pipeline")


def ensure_tables() -> None:
    # In production Alembic owns the schema (run at deploy via
    # scripts/run_migrations.py), so request-time DDL is both unnecessary and a
    # hazard -- skip it. In dev/test this lazily creates the auth/deal tables
    # (seed_db only creates the data tables) so the suite needs no separate
    # migration step. User first: DealQuery.owner_id is a foreign key into it.
    if config.IS_PRODUCTION:
        return
    Base.metadata.create_all(get_engine(), tables=[User.__table__, DealQuery.__table__, AuditLog.__table__])


def _persist(query_id: int, state_dict: dict, status: str) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None:
            return
        row.query_type = state_dict.get("query_type")
        row.deal_state = state_dict
        row.agent_trace = state_dict.get("agent_trace", [])
        row.status = status
        session.add(row)

        for entry in state_dict.get("agent_trace", []):
            session.add(
                AuditLog(query_id=query_id, event_type=f"agent:{entry.get('agent')}", event_payload=entry)
            )
        session.commit()


def _mark_running(query_id: int) -> None:
    """Flips status to 'running' and bumps attempt_count the moment the
    worker thread actually picks up the job -- separate from _persist so this
    still records "an attempt was made" even if the pipeline crashes before
    producing any state at all (e.g. get_deal_pipeline() itself raising)."""
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None:
            return
        row.status = "running"
        row.attempt_count = (row.attempt_count or 0) + 1
        session.add(row)
        session.commit()


def _run_sync(query_id: int, raw_query: str, loop: asyncio.AbstractEventLoop) -> None:
    query_id_str = str(query_id)
    last_state: dict = {"query_id": query_id_str, "raw_query": raw_query, "agent_trace": []}
    _mark_running(query_id)
    try:
        pipeline = get_deal_pipeline()
        initial_state = DealState(query_id=query_id_str, raw_query=raw_query)
        last_state = initial_state.model_dump()
        for state_dict in pipeline.stream(initial_state.model_dump(), stream_mode="values"):
            last_state = state_dict
            publish_threadsafe(loop, query_id_str, {"type": "state", "data": state_dict})
        _persist(query_id, last_state, status="done")
        publish_threadsafe(loop, query_id_str, {"type": "complete", "data": last_state})
    except Exception as exc:  # noqa: BLE001
        log.exception("Pipeline run failed for query_id=%s", query_id)
        last_state.setdefault("agent_trace", []).append(
            {"agent": "pipeline", "status": "error", "detail": str(exc)}
        )
        _persist(query_id, last_state, status="failed")
        publish_threadsafe(loop, query_id_str, {"type": "error", "detail": str(exc)})


async def run_pipeline(query_id: int, raw_query: str) -> None:
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(_run_sync, query_id, raw_query, loop)


def create_deal_query(raw_query: str, owner_id: int) -> int:
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = DealQuery(
            owner_id=owner_id,
            raw_query=raw_query,
            query_type=None,
            deal_state=None,
            agent_trace=[],
            status="pending",
            attempt_count=0,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.query_id


def get_deal_query(query_id: int) -> dict | None:
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None:
            return None
        return {
            "query_id": row.query_id,
            "owner_id": row.owner_id,
            "raw_query": row.raw_query,
            "query_type": row.query_type,
            "deal_state": row.deal_state,
            "agent_trace": row.agent_trace,
            "status": row.status,
            "attempt_count": row.attempt_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "share_token": row.share_token,
        }


def set_share_token(query_id: int, owner_id: int) -> str | None:
    """Idempotent: returns the existing token if this deal is already shared,
    otherwise mints one. None means the deal doesn't exist or isn't owned by
    this user -- callers should 404 either way (see _get_owned_deal)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None or row.owner_id != owner_id:
            return None
        if not row.share_token:
            row.share_token = secrets.token_urlsafe(24)
            session.commit()
        return row.share_token


def revoke_share_token(query_id: int, owner_id: int) -> bool:
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None or row.owner_id != owner_id:
            return False
        row.share_token = None
        session.commit()
        return True


def get_shared_memo(share_token: str) -> dict | None:
    """Public lookup by share token -- deliberately returns only the memo
    prose and enough context to render it, never the full deal_state (raw
    comps/valuation internals were never part of what "share this memo"
    means, and this endpoint has no owner check by design since the token
    itself is the capability)."""
    from sqlalchemy import select

    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.execute(
            select(DealQuery).where(DealQuery.share_token == share_token)
        ).scalar_one_or_none()
        if row is None:
            return None
        memo_markdown = (row.deal_state or {}).get("memo_markdown")
        if not memo_markdown:
            return None
        return {
            "memo_markdown": memo_markdown,
            "raw_query": row.raw_query,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


def list_deal_queries(owner_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    """Summary rows for the current user's deals, newest first (deal-history
    page). Excludes the heavy deal_state/agent_trace blobs -- just enough to
    render a list and link into each deal."""
    from sqlalchemy import select

    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.execute(
                select(DealQuery)
                .where(DealQuery.owner_id == owner_id)
                .order_by(DealQuery.created_at.desc(), DealQuery.query_id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return [
            {
                "query_id": r.query_id,
                "raw_query": r.raw_query,
                "query_type": r.query_type,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

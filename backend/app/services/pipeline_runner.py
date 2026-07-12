"""Runs the LangGraph deal pipeline in a worker thread, streaming state
snapshots to any WS subscribers and persisting the result to Postgres."""
from __future__ import annotations

import asyncio
import logging

from app.agents.graph import get_deal_pipeline
from app.db import get_engine, get_session_factory
from app.deal_state import DealState
from app.models import AuditLog, Base, DealQuery, User
from app.streaming import publish_threadsafe

log = logging.getLogger("sakan.pipeline")


def ensure_tables() -> None:
    # User first: DealQuery.owner_id is a foreign key into it.
    Base.metadata.create_all(get_engine(), tables=[User.__table__, DealQuery.__table__, AuditLog.__table__])


def _persist(query_id: int, state_dict: dict) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.get(DealQuery, query_id)
        if row is None:
            return
        row.query_type = state_dict.get("query_type")
        row.deal_state = state_dict
        row.agent_trace = state_dict.get("agent_trace", [])
        session.add(row)

        for entry in state_dict.get("agent_trace", []):
            session.add(
                AuditLog(query_id=query_id, event_type=f"agent:{entry.get('agent')}", event_payload=entry)
            )
        session.commit()


def _run_sync(query_id: int, raw_query: str, loop: asyncio.AbstractEventLoop) -> None:
    query_id_str = str(query_id)
    last_state: dict = {"query_id": query_id_str, "raw_query": raw_query, "agent_trace": []}
    try:
        pipeline = get_deal_pipeline()
        initial_state = DealState(query_id=query_id_str, raw_query=raw_query)
        last_state = initial_state.model_dump()
        for state_dict in pipeline.stream(initial_state.model_dump(), stream_mode="values"):
            last_state = state_dict
            publish_threadsafe(loop, query_id_str, {"type": "state", "data": state_dict})
        _persist(query_id, last_state)
        publish_threadsafe(loop, query_id_str, {"type": "complete", "data": last_state})
    except Exception as exc:  # noqa: BLE001
        log.exception("Pipeline run failed for query_id=%s", query_id)
        last_state.setdefault("agent_trace", []).append(
            {"agent": "pipeline", "status": "error", "detail": str(exc)}
        )
        _persist(query_id, last_state)
        publish_threadsafe(loop, query_id_str, {"type": "error", "detail": str(exc)})


async def run_pipeline(query_id: int, raw_query: str) -> None:
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(_run_sync, query_id, raw_query, loop)


def create_deal_query(raw_query: str, owner_id: int) -> int:
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = DealQuery(owner_id=owner_id, raw_query=raw_query, query_type=None, deal_state=None, agent_trace=[])
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
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

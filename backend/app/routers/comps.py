from __future__ import annotations

from fastapi import APIRouter

from app.cache import cached
from app.db import get_session_factory
from app.services.comps_service import query_transactions_sql, semantic_rerank

router = APIRouter(prefix="/comps", tags=["comps"])


@router.get("")
@cached(ttl_seconds=30)
async def list_comps(
    community: str | None = None,
    bedrooms: int | None = None,
    type: str | None = None,
    budget_min: float | None = None,
    budget_max: float | None = None,
    q: str | None = None,
    limit: int = 25,
) -> list[dict]:
    session_factory = get_session_factory()
    with session_factory() as session:
        comps = query_transactions_sql(
            session,
            community=community,
            property_type=type,
            bedrooms=bedrooms,
            budget_range=(budget_min, budget_max),
            limit=limit,
        )
    if q:
        comps = semantic_rerank(comps, query=q, top_k=min(limit, len(comps)))
    return comps

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.cache import cached
from app.db import get_session_factory
from app.models import Building, Developer, OffPlanProject, Transaction

router = APIRouter(prefix="/market", tags=["market"])

# Real-estate aggregates don't need second-by-second freshness -- a short TTL
# absorbs repeated identical requests (the ticker in particular polls) without
# ever recomputing a Postgres GROUP BY more than once per window.
_TICKER_TTL_SECONDS = 30
_TRENDS_TTL_SECONDS = 60


@router.get("/ticker")
@cached(ttl_seconds=_TICKER_TTL_SECONDS)
async def market_ticker(limit: int = 20) -> list[dict]:
    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = (
            select(Transaction, Building.name.label("building_name"))
            .join(Building, Transaction.building_id == Building.building_id, isouter=True)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        rows = session.execute(stmt).all()

    return [
        {
            "building": building_name or txn.building_id,
            "community": txn.community,
            "beds": txn.bedrooms,
            "price": float(txn.price_aed) if txn.price_aed is not None else None,
            "type": txn.transaction_type,
        }
        for txn, building_name in rows
    ]


@router.get("/trends")
@cached(ttl_seconds=_TRENDS_TTL_SECONDS)
async def market_trends(view: str = "summary", community: str | None = None, limit: int = 4) -> list[dict]:
    session_factory = get_session_factory()

    if view == "developers":
        with session_factory() as session:
            rows = session.execute(
                select(Developer).order_by(Developer.track_record_score.desc())
            ).scalars().all()
        return [
            {
                "developer_id": d.developer_id,
                "name": d.name,
                "track_record_score": d.track_record_score,
                "active_projects_count": d.active_projects_count,
                "delivery_delay_rate": float(d.delivery_delay_rate) if d.delivery_delay_rate is not None else None,
            }
            for d in rows
        ]

    if view == "off_plan":
        with session_factory() as session:
            rows = session.execute(
                select(OffPlanProject).order_by(OffPlanProject.percent_sold.desc())
            ).scalars().all()
        return [
            {
                "project_id": p.project_id,
                "name": p.name,
                "community": p.community,
                "percent_sold": float(p.percent_sold) if p.percent_sold is not None else None,
            }
            for p in rows
        ]

    if view == "timeseries":
        with session_factory() as session:
            dialect = session.get_bind().dialect.name
            month_expr = (
                func.strftime("%Y-%m", Transaction.transaction_date)
                if dialect == "sqlite"
                else func.to_char(Transaction.transaction_date, "YYYY-MM")
            )
            stmt = (
                select(
                    Transaction.community,
                    month_expr.label("month"),
                    func.avg(Transaction.price_per_sqft).label("avg_price_per_sqft"),
                )
                .group_by(Transaction.community, month_expr)
                .order_by(month_expr)
            )
            if community:
                stmt = stmt.where(Transaction.community == community)
            rows = session.execute(stmt).all()
        return [
            {"community": c, "month": m, "avg_price_per_sqft": round(float(p), 2) if p is not None else None}
            for c, m, p in rows
        ]

    # default: view == "summary" -- avg price/sqft by community, top N
    with session_factory() as session:
        stmt = (
            select(Transaction.community, func.avg(Transaction.price_per_sqft).label("avg_price_per_sqft"))
            .group_by(Transaction.community)
            .order_by(func.avg(Transaction.price_per_sqft).desc())
            .limit(limit)
        )
        rows = session.execute(stmt).all()
    return [
        {"community": c, "avg_price_per_sqft": round(float(p), 2) if p is not None else None} for c, p in rows
    ]

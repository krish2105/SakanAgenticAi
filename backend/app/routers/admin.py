"""Admin-only endpoints, gated by require_role("Admin"). Small on purpose --
its job is to make the previously-dead `role` column load-bearing and give RBAC
a real enforcement point."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth import require_role
from app.db import get_session_factory
from app.models import DealQuery, User
from app.services.billing_service import PLANS

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(_: User = Depends(require_role("Admin"))) -> dict:
    """Platform counts. 403 for any non-Admin (enforced by require_role)."""
    session_factory = get_session_factory()
    with session_factory() as session:
        total_users = session.scalar(select(func.count(User.user_id))) or 0
        verified_users = (
            session.scalar(select(func.count(User.user_id)).where(User.email_verified.is_(True))) or 0
        )
        total_deals = session.scalar(select(func.count(DealQuery.query_id))) or 0
        by_tier = dict(
            session.execute(select(User.tier, func.count(User.user_id)).group_by(User.tier)).all()
        )
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "total_deals": total_deals,
        "users_by_tier": by_tier,
    }


@router.get("/users")
async def admin_list_users(
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
    _: User = Depends(require_role("Admin")),
) -> dict:
    """Search/list users by email or name, paginated. `q` matches either
    field case-insensitively as a substring."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = select(User).order_by(User.created_at.desc())
        if q:
            like = f"%{q}%"
            stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = session.execute(stmt.limit(limit).offset(offset)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "users": [
            {
                "user_id": u.user_id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "tier": u.tier,
                "email_verified": u.email_verified,
                "subscription_status": u.subscription_status,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ],
    }


class TierOverrideRequest(BaseModel):
    tier: str


@router.patch("/users/{user_id}/tier")
async def admin_override_tier(
    user_id: int,
    body: TierOverrideRequest,
    _: User = Depends(require_role("Admin")),
) -> dict:
    """Manually set a user's tier -- e.g. comping a pilot customer or fixing
    a Stripe webhook that never landed. Bypasses billing entirely; does not
    touch stripe_subscription_id/subscription_status."""
    if body.tier not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown tier {body.tier!r}. Valid: {sorted(PLANS)}")

    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.tier = body.tier
        session.commit()
        return {"user_id": user_id, "tier": user.tier}


@router.get("/query-volume")
async def admin_query_volume(days: int = 30, _: User = Depends(require_role("Admin"))) -> list[dict]:
    """Daily deal-query counts for the last N days, oldest first -- feeds a
    simple volume chart on the admin dashboard."""
    days = max(1, min(days, 180))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    session_factory = get_session_factory()
    with session_factory() as session:
        dialect = session.get_bind().dialect.name
        day_expr = (
            func.strftime("%Y-%m-%d", DealQuery.created_at)
            if dialect == "sqlite"
            else func.to_char(DealQuery.created_at, "YYYY-MM-DD")
        )
        stmt = (
            select(day_expr.label("day"), func.count(DealQuery.query_id))
            .where(DealQuery.created_at >= since)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        rows = session.execute(stmt).all()

    return [{"day": day, "count": count} for day, count in rows]

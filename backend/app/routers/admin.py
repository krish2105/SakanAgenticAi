"""Admin-only endpoints, gated by require_role("Admin"). Small on purpose --
its job is to make the previously-dead `role` column load-bearing and give RBAC
a real enforcement point."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.auth import require_role
from app.db import get_session_factory
from app.models import DealQuery, User

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

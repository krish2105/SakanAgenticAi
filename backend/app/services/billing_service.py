"""Subscription tiers, quota enforcement, and the Stripe price-id <-> tier
mapping (Phase B "paid launch" of the MVP roadmap).

Deliberately narrow: gates the expensive full-pipeline endpoint
(/deals/query) by a monthly count of DealQuery rows rather than a separate
usage-counter table that needs its own reset job -- "how many rows did this
user create since the start of the current UTC month" is cheap to compute
and needs no scheduled reset. Comps search (/comps) stays ungated for every
tier, matching the pricing table ("unlimited comps" even on Starter).

Team's "per 5 seats" language in the pricing table describes seat-based
billing that isn't modeled here -- Team and Enterprise both get an
unmetered full-pipeline quota per user account, and multi-seat/shared
workspace billing is left for a future iteration, not silently faked.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config as app_config
from app.models import DealQuery, User

# monthly_query_limit is the cap on /deals/query (full pipeline) calls per
# calendar month; None means unmetered.
PLANS: dict[str, dict] = {
    "starter": {"label": "Starter", "price_aed_monthly": 0, "monthly_query_limit": 5},
    "pro": {"label": "Pro", "price_aed_monthly": 299, "monthly_query_limit": 50},
    "team": {"label": "Team", "price_aed_monthly": 999, "monthly_query_limit": None},
    "enterprise": {"label": "Enterprise", "price_aed_monthly": None, "monthly_query_limit": None},  # contact sales
}

# Stripe price ids live in config (env vars), read through app_config (not
# imported by value) so tests can monkeypatch app.config.STRIPE_PRICE_ID_*
# and have it actually take effect here.
_PRICE_ENV_ATTR = {"pro": "STRIPE_PRICE_ID_PRO", "team": "STRIPE_PRICE_ID_TEAM"}


def stripe_price_id_for(tier: str) -> str | None:
    attr = _PRICE_ENV_ATTR.get(tier)
    return getattr(app_config, attr) if attr else None


def tier_for_price_id(price_id: str | None) -> str | None:
    if not price_id:
        return None
    for tier in _PRICE_ENV_ATTR:
        if stripe_price_id_for(tier) == price_id:
            return tier
    return None


def _month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_monthly_query_count(session: Session, owner_id: int) -> int:
    return session.scalar(
        select(func.count(DealQuery.query_id)).where(
            DealQuery.owner_id == owner_id,
            DealQuery.created_at >= _month_start(),
        )
    ) or 0


def get_daily_query_counts(session: Session, owner_id: int) -> list[dict]:
    """Per-day full-pipeline query counts since the start of the current UTC
    month, for the usage-over-time chart on the billing page. Sourced from
    the same DealQuery rows enforce_quota already counts -- no separate
    usage-log table, same reasoning as get_monthly_query_count's docstring.

    Grouped in Python rather than via SQL cast(..., Date)/GROUP BY: this
    tier's monthly quota (5-50 full-pipeline queries) keeps the row count
    trivially small, and SQLite's DATE cast doesn't reliably round-trip
    through SQLAlchemy's Date type processor (raises on a DATETIME-stored
    column), while a portable dialect-branching query isn't worth it for
    a query volume this small."""
    timestamps = session.scalars(
        select(DealQuery.created_at).where(
            DealQuery.owner_id == owner_id, DealQuery.created_at >= _month_start()
        )
    ).all()
    counts: dict[str, int] = {}
    for ts in timestamps:
        day = ts.date().isoformat()
        counts[day] = counts.get(day, 0) + 1
    return [{"date": day, "count": count} for day, count in sorted(counts.items())]


def quota_status(session: Session, user: User) -> dict:
    plan = PLANS.get(user.tier, PLANS["starter"])
    used = get_monthly_query_count(session, user.user_id)
    limit = plan["monthly_query_limit"]
    return {
        "tier": user.tier,
        "label": plan["label"],
        "monthly_query_limit": limit,
        "queries_used_this_month": used,
        "queries_remaining": None if limit is None else max(0, limit - used),
        "subscription_status": user.subscription_status,
    }


def enforce_quota(session: Session, user: User) -> None:
    """Raises 402 Payment Required if the user has exhausted this month's
    full-pipeline query quota for their tier. Called before a new deal query
    is created, not after -- the point is to stop the expensive Anthropic
    call from happening, not to bill for it after the fact."""
    status = quota_status(session, user)
    limit = status["monthly_query_limit"]
    if limit is not None and status["queries_used_this_month"] >= limit:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly query limit reached ({limit} full-pipeline queries on the "
                f"{status['label']} plan). Upgrade at /billing to continue this month."
            ),
        )

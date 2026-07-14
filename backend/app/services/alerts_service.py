"""Saved-search email digests (Phase 25): a periodic "here's what currently
matches your saved filter" email, not a "new listing" alert -- see
app/models.py's SavedSearch docstring for why that distinction is load-bearing
here (Transaction has no insertion timestamp to prove genuine novelty).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SavedSearch, User
from app.services.comps_service import query_transactions_sql
from app.services.email import send_email

DIGEST_MAX_COMPS = 5
MIN_DIGEST_INTERVAL = timedelta(hours=20)  # a bit under a day, tolerant of cron jitter


def create_saved_search(
    session: Session,
    owner_id: int,
    *,
    community: str | None,
    property_type: str | None,
    bedrooms: int | None,
    budget_min: float | None,
    budget_max: float | None,
) -> SavedSearch:
    row = SavedSearch(
        owner_id=owner_id,
        community=community,
        property_type=property_type,
        bedrooms=bedrooms,
        budget_min=budget_min,
        budget_max=budget_max,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_saved_searches(session: Session, owner_id: int) -> list[SavedSearch]:
    return list(
        session.scalars(
            select(SavedSearch).where(SavedSearch.owner_id == owner_id).order_by(SavedSearch.created_at.desc())
        ).all()
    )


def delete_saved_search(session: Session, owner_id: int, saved_search_id: int) -> bool:
    """Ownership-scoped, same pattern as api_keys.revoke_api_key."""
    row = session.scalar(
        select(SavedSearch).where(SavedSearch.saved_search_id == saved_search_id, SavedSearch.owner_id == owner_id)
    )
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def matching_comps_for_search(session: Session, search: SavedSearch, limit: int = DIGEST_MAX_COMPS) -> list[dict]:
    return query_transactions_sql(
        session,
        community=search.community,
        property_type=search.property_type,
        bedrooms=search.bedrooms,
        budget_range=(float(search.budget_min) if search.budget_min is not None else None,
                      float(search.budget_max) if search.budget_max is not None else None),
        limit=limit,
    )


def _digest_body(search: SavedSearch, comps: list[dict]) -> str:
    filters = ", ".join(
        f"{label}: {value}"
        for label, value in [
            ("Community", search.community),
            ("Type", search.property_type),
            ("Bedrooms", search.bedrooms),
            ("Budget min", search.budget_min),
            ("Budget max", search.budget_max),
        ]
        if value is not None
    ) or "all comps"

    lines = [f"Your saved search ({filters}) currently matches {len(comps)} comp(s):", ""]
    for c in comps:
        lines.append(f"- {c['building']}, {c['community']} — AED {c['price']:,.0f} ({c['bedrooms']}BR)")
    lines.append("")
    lines.append("View more in the Comps Explorer.")
    return "\n".join(lines)


def send_digest_for_search(session: Session, search: SavedSearch, user: User) -> bool:
    """Sends the digest email and stamps last_notified_at. Returns False
    (and sends nothing) when there are currently no matches -- an empty
    digest isn't useful and would just be noise."""
    comps = matching_comps_for_search(session, search)
    if not comps:
        return False
    send_email(user.email, "Sakan AI — your saved search digest", _digest_body(search, comps))
    search.last_notified_at = datetime.now(timezone.utc)
    session.add(search)
    session.commit()
    return True


def run_all_digests(session: Session) -> int:
    """Entry point for scripts/send_search_digests.py. Sends a digest for
    every saved search that currently has matches and hasn't been notified
    within MIN_DIGEST_INTERVAL -- the interval guard exists so a manually
    re-triggered workflow run (or a cron misfire) can't spam a user with
    duplicate digests; the intended cadence is still set by how often the
    scheduled workflow runs. Returns the number of digests actually sent."""
    now = datetime.now(timezone.utc)
    searches = session.scalars(select(SavedSearch)).all()
    sent = 0
    for search in searches:
        if search.last_notified_at is not None:
            last = search.last_notified_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if now - last < MIN_DIGEST_INTERVAL:
                continue
        user = session.get(User, search.owner_id)
        if user is None:
            continue
        if send_digest_for_search(session, search, user):
            sent += 1
    return sent

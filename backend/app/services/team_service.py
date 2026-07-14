"""Team/seat billing (Phase 11c): Organization membership, invites, and
best-effort Stripe seat-quantity sync.

Deliberately scoped: an invite targets an *existing* Sakan AI account by
email (looked up at invite time), not an arbitrary unregistered address --
supporting invite-before-signup would need its own pending-invite-by-email
flow that survives registration, which is a bigger feature than "seat-based
billing isn't modeled" (the gap this phase actually closes) calls for. The
owner manages membership; members share the org's unmetered Team quota.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Organization, TeamInvite, User

log = logging.getLogger("sakan.team")

INVITE_EXPIRE_DAYS = 7


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_organization_for_owner(session: Session, owner_user_id: int) -> Organization | None:
    return session.scalar(select(Organization).where(Organization.owner_user_id == owner_user_id))


def ensure_organization(session: Session, owner: User) -> Organization:
    """Get-or-create the Team org for a user who just became (or already is)
    a Team-tier owner. Idempotent -- safe to call on every subscription
    webhook that resolves to the team tier, not just the first one."""
    org = get_organization_for_owner(session, owner.user_id)
    if org is not None:
        return org

    org = Organization(
        name=f"{owner.full_name or owner.email}'s team",
        owner_user_id=owner.user_id,
        stripe_subscription_id=owner.stripe_subscription_id,
        seat_count=1,
    )
    session.add(org)
    session.flush()  # populate organization_id before it's referenced
    owner.organization_id = org.organization_id
    session.add(owner)
    session.commit()
    session.refresh(org)
    return org


def sync_stripe_seats(org: Organization) -> None:
    """Best-effort: update the Stripe subscription's item quantity to match
    org.seat_count. Failure here (Stripe unreachable, subscription missing,
    Stripe not configured at all) must never block an invite/accept/remove
    from completing -- a stale Stripe quantity is a billing reconciliation
    problem to notice and fix, not a reason to block a teammate joining."""
    if not config.STRIPE_SECRET_KEY or not org.stripe_subscription_id:
        return
    try:
        import stripe

        stripe.api_key = config.STRIPE_SECRET_KEY
        subscription = stripe.Subscription.retrieve(org.stripe_subscription_id)
        item_id = subscription["items"]["data"][0]["id"]
        stripe.Subscription.modify(
            org.stripe_subscription_id, items=[{"id": item_id, "quantity": org.seat_count}]
        )
    except Exception:  # noqa: BLE001
        log.exception(
            "Failed to sync Stripe seat quantity for org_id=%s (seat_count=%s) -- "
            "membership change still applied; billing will need manual reconciliation.",
            org.organization_id,
            org.seat_count,
        )


def invite_member(session: Session, org: Organization, invited_email: str) -> tuple[TeamInvite, str]:
    invited_user = session.scalar(select(User).where(User.email == invited_email.lower()))
    if invited_user is None:
        raise HTTPException(
            status_code=404,
            detail="No Sakan AI account with that email yet -- ask them to register first, then invite them.",
        )
    if invited_user.organization_id is not None:
        raise HTTPException(status_code=409, detail="That user already belongs to a team.")

    raw = secrets.token_urlsafe(32)
    invite = TeamInvite(
        organization_id=org.organization_id,
        invited_user_id=invited_user.user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRE_DAYS),
    )
    session.add(invite)
    session.commit()
    return invite, raw


def accept_invite(session: Session, raw_token: str, accepting_user: User) -> Organization:
    invite = session.scalar(select(TeamInvite).where(TeamInvite.token_hash == _hash_token(raw_token)))
    if invite is None or invite.accepted:
        raise HTTPException(status_code=400, detail="Invalid or already-used invite.")
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This invite has expired.")
    if invite.invited_user_id != accepting_user.user_id:
        raise HTTPException(status_code=403, detail="This invite was issued to a different account.")

    org = session.get(Organization, invite.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="This team no longer exists.")

    invite.accepted = True
    accepting_user.organization_id = org.organization_id
    org.seat_count += 1
    session.add_all([invite, accepting_user, org])
    session.commit()
    session.refresh(org)

    sync_stripe_seats(org)
    return org


def remove_member(session: Session, org: Organization, member: User) -> None:
    if member.organization_id != org.organization_id:
        raise HTTPException(status_code=404, detail="That user isn't a member of your team.")
    if member.user_id == org.owner_user_id:
        raise HTTPException(status_code=400, detail="The team owner can't be removed -- cancel the subscription instead.")

    member.organization_id = None
    org.seat_count = max(1, org.seat_count - 1)
    session.add_all([member, org])
    session.commit()
    session.refresh(org)

    sync_stripe_seats(org)


def list_members(session: Session, org: Organization) -> list[User]:
    # The owner's own organization_id is set in ensure_organization() just
    # like any accepted member's, so a single equality filter covers both.
    return session.scalars(select(User).where(User.organization_id == org.organization_id)).all()

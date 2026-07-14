"""Partner/embed API key issuance + lookup (Phase 20).

Same opaque-token pattern as app/auth.py's refresh/reset/verify tokens:
only a SHA-256 hash is persisted, so a DB leak hands over no usable key.
The raw key is returned to its owner exactly once, at creation.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import ApiKey, User

KEY_PREFIX = "sk_live_"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_api_key(session, user_id: int, name: str) -> str:
    raw = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    session.add(
        ApiKey(
            user_id=user_id,
            name=name,
            key_hash=_hash_key(raw),
            key_prefix=raw[: len(KEY_PREFIX) + 8],
            revoked=False,
        )
    )
    return raw


def list_api_keys(session, user_id: int) -> list[ApiKey]:
    rows = session.scalars(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.revoked.is_(False))
        .order_by(ApiKey.created_at.desc())
    ).all()
    return list(rows)


def revoke_api_key(session, user_id: int, api_key_id: int) -> bool:
    """Ownership-scoped, same as auth.revoke_session -- one user can never
    revoke another's key by guessing an id."""
    row = session.scalar(
        select(ApiKey).where(ApiKey.api_key_id == api_key_id, ApiKey.user_id == user_id)
    )
    if row is None:
        return False
    row.revoked = True
    session.add(row)
    return True


def get_user_for_api_key(session, raw_key: str) -> User | None:
    row = session.scalar(select(ApiKey).where(ApiKey.key_hash == _hash_key(raw_key)))
    if row is None or row.revoked:
        return None
    row.last_used_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    return session.get(User, row.user_id)

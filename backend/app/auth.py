"""Password hashing, JWT issuance/verification, and the FastAPI dependencies
that enforce "a deal belongs to the user who created it" (Phase A of the MVP
roadmap -- see the strategy note for why this blocks even a design-partner
beta, not just a paid launch)."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config
from app.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from app.db import get_session_factory
from app.models import AuthToken, User

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- Opaque tokens (refresh / password-reset / email-verification) -----------
#
# These are high-entropy random strings, so a fast hash (SHA-256) is the right
# tool -- unlike passwords, they don't need bcrypt's deliberate slowness. Only
# the hash is persisted; the raw value is returned to the caller once and never
# stored, so a database leak yields no usable tokens.

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _issue_token(session, user_id: int, token_type: str, ttl: timedelta) -> str:
    raw = secrets.token_urlsafe(32)
    session.add(
        AuthToken(
            user_id=user_id,
            token_type=token_type,
            token_hash=_hash_token(raw),
            expires_at=datetime.now(timezone.utc) + ttl,
            revoked=False,
        )
    )
    return raw


def create_refresh_token(session, user_id: int) -> str:
    return _issue_token(
        session, user_id, "refresh", timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_reset_token(session, user_id: int) -> str:
    return _issue_token(
        session, user_id, "reset", timedelta(hours=config.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    )


def create_verify_token(session, user_id: int) -> str:
    return _issue_token(
        session, user_id, "verify", timedelta(hours=config.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS)
    )


def _lookup_token(session, raw: str, token_type: str) -> AuthToken | None:
    from sqlalchemy import select

    row = session.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == _hash_token(raw),
            AuthToken.token_type == token_type,
        )
    )
    if row is None or row.revoked:
        return None
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return row


def consume_single_use_token(session, raw: str, token_type: str) -> int | None:
    """Validate a reset/verify token and burn it (revoke) so it can't be reused.
    Returns the user_id or None."""
    row = _lookup_token(session, raw, token_type)
    if row is None:
        return None
    row.revoked = True
    session.add(row)
    return row.user_id


def rotate_refresh_token(session, raw: str) -> tuple[str, int] | None:
    """Validate a refresh token, revoke it, and issue a new one (rotation).
    Returns (new_raw_token, user_id) or None if invalid/expired/revoked."""
    row = _lookup_token(session, raw, "refresh")
    if row is None:
        return None
    row.revoked = True
    session.add(row)
    new_raw = create_refresh_token(session, row.user_id)
    return new_raw, row.user_id


def revoke_refresh_token(session, raw: str) -> None:
    row = _lookup_token(session, raw, "refresh")
    if row is not None:
        row.revoked = True
        session.add(row)


def revoke_all_refresh_tokens(session, user_id: int) -> None:
    """Used after a password reset -- log every session out."""
    from sqlalchemy import update

    session.execute(
        update(AuthToken)
        .where(AuthToken.user_id == user_id, AuthToken.token_type == "refresh")
        .values(revoked=True)
    )


def _load_user(user_id: int) -> User | None:
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        session.expunge(user)
        return user


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> User:
    """Standard HTTP dependency: requires a valid `Authorization: Bearer <token>` header."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = _load_user(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def require_role(*roles: str):
    """Dependency factory enforcing role-based access. Usage:
    `Depends(require_role("Admin"))`. The `role` column existed but was never
    checked anywhere -- this makes it load-bearing."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency


def get_current_user_ws(token: str | None = Query(default=None)) -> User | None:
    """Browser WebSocket clients can't set custom headers, so the token travels
    as a query param instead (?token=...). Returns None rather than raising --
    the WS route decides how to react (close the connection) so it can send a
    clean close frame instead of an HTTP error the browser can't see."""
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return _load_user(int(payload["sub"]))

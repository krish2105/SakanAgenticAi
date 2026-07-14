"""Partner/embed API (Phase 20): manage API keys, and a rate-limited,
read-only comps endpoint reachable outside the web app/WhatsApp/extension --
a free-to-build growth channel for a proptech tool wanting to embed Sakan
AI's comps data. No Stripe/billing tie-in yet (see app/models.py's ApiKey
docstring); gated purely by the per-key rate limit below.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app.api_keys import create_api_key, get_user_for_api_key, list_api_keys, revoke_api_key
from app.db import get_session_factory
from app.models import User
from app.ratelimit import client_ip_key, limiter
from app.services.comps_service import query_transactions_sql

router = APIRouter(prefix="/partner", tags=["partner"])


class ApiKeyCreateRequest(BaseModel):
    name: str


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreatedOut(ApiKeyOut):
    api_key: str  # only ever returned here, at creation


@router.post("/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
async def create_my_api_key(
    body: ApiKeyCreateRequest, current_user: User = Depends(get_current_user)
) -> ApiKeyCreatedOut:
    session_factory = get_session_factory()
    with session_factory() as session:
        raw = create_api_key(session, current_user.user_id, body.name)
        session.commit()
        row = list_api_keys(session, current_user.user_id)[0]
        return ApiKeyCreatedOut(
            id=row.api_key_id,
            name=row.name,
            key_prefix=row.key_prefix,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            api_key=raw,
        )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_my_api_keys(current_user: User = Depends(get_current_user)) -> list[ApiKeyOut]:
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = list_api_keys(session, current_user.user_id)
        return [
            ApiKeyOut(
                id=r.api_key_id,
                name=r.name,
                key_prefix=r.key_prefix,
                created_at=r.created_at,
                last_used_at=r.last_used_at,
            )
            for r in rows
        ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
async def delete_my_api_key(api_key_id: int, current_user: User = Depends(get_current_user)) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        found = revoke_api_key(session, current_user.user_id, api_key_id)
        if not found:
            raise HTTPException(status_code=404, detail="API key not found")
        session.commit()


def require_api_key(x_api_key: str | None = Header(default=None)) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    session_factory = get_session_factory()
    with session_factory() as session:
        user = get_user_for_api_key(session, x_api_key)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return user


def _api_key_rate_limit_key(request: Request) -> str:
    """Keyed per API key rather than IP, so partners sharing an egress IP
    (or a partner's own server making many calls) don't share one bucket --
    falls back to client_ip_key only for the pre-auth case where the header
    is simply absent (that request 401s from require_api_key regardless)."""
    return request.headers.get("x-api-key") or client_ip_key(request)


@router.get("/v1/comps")
@limiter.limit("60/minute", key_func=_api_key_rate_limit_key)
async def partner_comps(
    request: Request,
    community: str | None = None,
    bedrooms: int | None = None,
    type: str | None = None,
    budget_min: float | None = None,
    budget_max: float | None = None,
    limit: int = 25,
    user: User = Depends(require_api_key),
) -> list[dict]:
    del user  # authorizes the call; comps data itself isn't user-scoped
    session_factory = get_session_factory()
    with session_factory() as session:
        return query_transactions_sql(
            session,
            community=community,
            property_type=type,
            bedrooms=bedrooms,
            budget_range=(budget_min, budget_max),
            limit=min(limit, 100),
        )

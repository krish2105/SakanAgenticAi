from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_session_factory
from app.models import User
from app.services.alerts_service import create_saved_search, delete_saved_search, list_saved_searches

router = APIRouter(prefix="/alerts", tags=["alerts"])


class SavedSearchCreate(BaseModel):
    community: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    budget_min: float | None = None
    budget_max: float | None = None


class SavedSearchOut(BaseModel):
    id: int
    community: str | None
    property_type: str | None
    bedrooms: int | None
    budget_min: float | None
    budget_max: float | None
    created_at: datetime
    last_notified_at: datetime | None


def _to_out(row) -> SavedSearchOut:
    return SavedSearchOut(
        id=row.saved_search_id,
        community=row.community,
        property_type=row.property_type,
        bedrooms=row.bedrooms,
        budget_min=float(row.budget_min) if row.budget_min is not None else None,
        budget_max=float(row.budget_max) if row.budget_max is not None else None,
        created_at=row.created_at,
        last_notified_at=row.last_notified_at,
    )


@router.get("", response_model=list[SavedSearchOut])
async def list_my_saved_searches(current_user: User = Depends(get_current_user)) -> list[SavedSearchOut]:
    session_factory = get_session_factory()
    with session_factory() as session:
        return [_to_out(r) for r in list_saved_searches(session, current_user.user_id)]


@router.post("", response_model=SavedSearchOut, status_code=201)
async def add_saved_search(
    body: SavedSearchCreate, current_user: User = Depends(get_current_user)
) -> SavedSearchOut:
    session_factory = get_session_factory()
    with session_factory() as session:
        row = create_saved_search(
            session,
            current_user.user_id,
            community=body.community,
            property_type=body.property_type,
            bedrooms=body.bedrooms,
            budget_min=body.budget_min,
            budget_max=body.budget_max,
        )
        return _to_out(row)


@router.delete("/{saved_search_id}", status_code=204)
async def remove_saved_search(saved_search_id: int, current_user: User = Depends(get_current_user)) -> Response:
    session_factory = get_session_factory()
    with session_factory() as session:
        found = delete_saved_search(session, current_user.user_id, saved_search_id)
        if not found:
            raise HTTPException(status_code=404, detail="Saved search not found")
    return Response(status_code=204)

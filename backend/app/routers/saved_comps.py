from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_session_factory
from app.models import Transaction, User
from app.services.comps_service import (
    list_saved_transaction_ids,
    query_transactions_by_ids,
    save_comp,
    unsave_comp,
)

router = APIRouter(prefix="/comps/saved", tags=["saved-comps"])


class SaveCompRequest(BaseModel):
    transaction_id: str


@router.get("")
async def list_saved_comps(current_user: User = Depends(get_current_user)) -> list[dict]:
    session_factory = get_session_factory()
    with session_factory() as session:
        ids = list_saved_transaction_ids(session, current_user.user_id)
        return query_transactions_by_ids(session, ids)


@router.post("", status_code=201)
async def add_saved_comp(body: SaveCompRequest, current_user: User = Depends(get_current_user)) -> dict:
    session_factory = get_session_factory()
    with session_factory() as session:
        if session.get(Transaction, body.transaction_id) is None:
            raise HTTPException(status_code=404, detail="Unknown comp")
        save_comp(session, current_user.user_id, body.transaction_id)
    return {"transaction_id": body.transaction_id, "saved": True}


@router.delete("/{transaction_id}", status_code=204)
async def remove_saved_comp(transaction_id: str, current_user: User = Depends(get_current_user)) -> Response:
    session_factory = get_session_factory()
    with session_factory() as session:
        unsave_comp(session, current_user.user_id, transaction_id)
    return Response(status_code=204)

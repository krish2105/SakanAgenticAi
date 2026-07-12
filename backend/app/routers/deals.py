from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import get_current_user, get_current_user_ws
from app.db import get_session_factory
from app.models import User
from app.services.billing_service import enforce_quota
from app.services.pdf import markdown_to_pdf_bytes
from app.services.pipeline_runner import create_deal_query, ensure_tables, get_deal_query, run_pipeline
from app.streaming import subscribe, unsubscribe

router = APIRouter(prefix="/deals", tags=["deals"])
limiter = Limiter(key_func=get_remote_address)


class DealQueryRequest(BaseModel):
    raw_query: str


class DealQueryResponse(BaseModel):
    query_id: str


def _parse_query_id(query_id: str) -> int:
    try:
        return int(query_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deal query not found")


def _get_owned_deal(query_id: str, user_id: int) -> dict:
    """404s for both "doesn't exist" and "exists but isn't yours" -- returning
    403 for the latter would confirm to an attacker that a given query_id is
    valid, which is exactly the guessable-ID leak this is meant to close."""
    row = get_deal_query(_parse_query_id(query_id))
    if row is None or row.get("owner_id") != user_id:
        raise HTTPException(status_code=404, detail="Deal query not found")
    return row


@router.post("/query", response_model=DealQueryResponse, status_code=202)
@limiter.limit("10/minute")
async def submit_deal_query(
    request: Request,  # required by @limiter.limit -- slowapi reads client info off it
    body: DealQueryRequest,
    current_user: User = Depends(get_current_user),
) -> DealQueryResponse:
    if not body.raw_query or not body.raw_query.strip():
        raise HTTPException(status_code=422, detail="raw_query must not be empty")

    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        enforce_quota(session, current_user)

    query_id = create_deal_query(body.raw_query, owner_id=current_user.user_id)
    asyncio.create_task(run_pipeline(query_id, body.raw_query))
    return DealQueryResponse(query_id=str(query_id))


@router.get("/{query_id}")
async def get_deal(query_id: str, current_user: User = Depends(get_current_user)) -> dict:
    row = _get_owned_deal(query_id, current_user.user_id)
    return row["deal_state"] or {
        "query_id": query_id,
        "raw_query": row["raw_query"],
        "agent_trace": [],
        "retrieved_comps": [],
        "retrieved_clauses": [],
        "compliance_flags": [],
    }


@router.get("/{query_id}/trace")
async def get_deal_trace(query_id: str, current_user: User = Depends(get_current_user)) -> dict:
    row = _get_owned_deal(query_id, current_user.user_id)
    return {"query_id": query_id, "agent_trace": row["agent_trace"] or []}


@router.get("/{query_id}/memo")
async def get_deal_memo(query_id: str, format: str = "json", current_user: User = Depends(get_current_user)):
    row = _get_owned_deal(query_id, current_user.user_id)
    if not row["deal_state"]:
        raise HTTPException(status_code=404, detail="Deal query not found")

    memo_markdown = row["deal_state"].get("memo_markdown")
    if not memo_markdown:
        raise HTTPException(status_code=404, detail="Memo not yet generated for this deal")

    if format == "pdf":
        pdf_bytes = markdown_to_pdf_bytes(memo_markdown)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="sakan-memo-{query_id}.pdf"'},
        )

    return {"query_id": query_id, "memo_markdown": memo_markdown}


async def _stream_deal(websocket: WebSocket, query_id: str) -> None:
    user = get_current_user_ws(websocket.query_params.get("token"))
    if user is None:
        await websocket.close(code=4401)  # custom app-level code: unauthenticated
        return

    if not query_id.isdigit():
        await websocket.close(code=4404)
        return
    row = get_deal_query(int(query_id))
    if row is None or row.get("owner_id") != user.user_id:
        await websocket.close(code=4404)  # custom app-level code: not found / not yours
        return

    await websocket.accept()
    queue = await subscribe(query_id)
    try:
        if row["deal_state"]:
            await websocket.send_json({"type": "state", "data": row["deal_state"]})

        while True:
            message = await queue.get()
            await websocket.send_json(message)
            if message.get("type") in ("complete", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await unsubscribe(query_id, queue)

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app import config
from app.auth import get_current_user, get_current_user_ws
from app.ratelimit import client_ip_key, limiter  # noqa: F401  (client_ip_key re-exported for tests)
from app.db import get_session_factory
from app.models import User
from app.services.billing_service import enforce_quota
from app.services.pdf import markdown_to_pdf_bytes
from app.services.pipeline_runner import (
    create_deal_query,
    ensure_tables,
    get_deal_query,
    get_shared_memo,
    list_deal_queries,
    revoke_share_token,
    run_pipeline,
    set_share_token,
)
from app.streaming import subscribe, unsubscribe

router = APIRouter(prefix="/deals", tags=["deals"])

# asyncio's event loop only keeps a *weak* reference to tasks it's running --
# a fire-and-forget asyncio.create_task() with no other reference can be
# garbage-collected mid-run, silently, with no exception and no log line.
# This set holds a strong reference until each task finishes so the pipeline
# actually gets to completion instead of vanishing partway through.
_background_tasks: set[asyncio.Task] = set()


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
    task = asyncio.create_task(run_pipeline(query_id, body.raw_query))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return DealQueryResponse(query_id=str(query_id))


@router.get("")
async def list_deals(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
) -> dict:
    """The current user's deal history, newest first. Paginated; only the
    caller's own deals (owner-scoped, same as the single-deal fetch)."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    deals = list_deal_queries(current_user.user_id, limit=limit, offset=offset)
    return {"deals": deals, "limit": limit, "offset": offset}


@router.get("/{query_id}")
async def get_deal(query_id: str, current_user: User = Depends(get_current_user)) -> dict:
    row = _get_owned_deal(query_id, current_user.user_id)
    state = row["deal_state"] or {
        "query_id": query_id,
        "raw_query": row["raw_query"],
        "agent_trace": [],
        "retrieved_comps": [],
        "retrieved_clauses": [],
        "compliance_flags": [],
    }
    # job_status is the persisted, authoritative record (Phase 4) -- distinct
    # from agent_trace, which can't tell "never started" apart from "started
    # and the process died mid-run". Merged in rather than embedded in
    # deal_state itself, which is the pipeline's own output, not job metadata.
    return {**state, "job_status": row["status"], "attempt_count": row["attempt_count"]}


@router.post("/{query_id}/retry", status_code=202)
async def retry_deal(query_id: str, current_user: User = Depends(get_current_user)) -> DealQueryResponse:
    """Re-runs a deal query that failed. Only valid from status='failed' --
    retrying a 'done' run would silently overwrite a good result, and
    retrying a 'pending'/'running' one risks a second concurrent run of the
    same query_id. Free: quota is charged once at creation (by row count),
    not per attempt, so a retry never costs the user anything extra."""
    row = _get_owned_deal(query_id, current_user.user_id)
    if row["status"] != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Only a failed deal query can be retried (current status: {row['status']}).",
        )

    parsed_id = _parse_query_id(query_id)
    task = asyncio.create_task(run_pipeline(parsed_id, row["raw_query"]))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return DealQueryResponse(query_id=query_id)


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
        state = row["deal_state"]
        valuation = {
            "low": state.get("valuation_low"),
            "high": state.get("valuation_high"),
            "comps": state.get("retrieved_comps") or [],
        }
        pdf_bytes = markdown_to_pdf_bytes(memo_markdown, valuation=valuation)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="sakan-memo-{query_id}.pdf"'},
        )

    return {"query_id": query_id, "memo_markdown": memo_markdown}


class ShareResponse(BaseModel):
    share_token: str
    share_url: str


@router.post("/{query_id}/share", response_model=ShareResponse)
async def share_deal_memo(query_id: str, current_user: User = Depends(get_current_user)) -> ShareResponse:
    """Mints (or returns the existing) public share link for this deal's
    memo. Idempotent on purpose -- clicking "Share" twice must not rotate
    the link out from under someone who already sent it out."""
    row = _get_owned_deal(query_id, current_user.user_id)
    if not (row.get("deal_state") or {}).get("memo_markdown"):
        raise HTTPException(status_code=409, detail="Memo not yet generated for this deal")

    token = set_share_token(_parse_query_id(query_id), current_user.user_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Deal query not found")
    return ShareResponse(share_token=token, share_url=f"{config.FRONTEND_URL}/memo/{token}")


@router.delete("/{query_id}/share", status_code=204)
async def unshare_deal_memo(query_id: str, current_user: User = Depends(get_current_user)) -> Response:
    _get_owned_deal(query_id, current_user.user_id)
    revoke_share_token(_parse_query_id(query_id), current_user.user_id)
    return Response(status_code=204)


@router.get("/shared/{share_token}")
@limiter.limit("30/minute")
async def get_shared_deal_memo(request: Request, share_token: str) -> dict:
    """Deliberately no auth dependency -- the token itself is the
    capability, same as any unlisted-link share (Google Docs, Figma, etc).
    Rate-limited (not auth-gated) since the token space is high-entropy
    enough that brute force isn't the threat model, but scraping is."""
    result = get_shared_memo(share_token)
    if result is None:
        raise HTTPException(status_code=404, detail="This share link is invalid or has been revoked")
    return result


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

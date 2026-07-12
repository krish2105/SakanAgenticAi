from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.pdf import markdown_to_pdf_bytes
from app.services.pipeline_runner import create_deal_query, get_deal_query, run_pipeline
from app.streaming import subscribe, unsubscribe

router = APIRouter(prefix="/deals", tags=["deals"])


class DealQueryRequest(BaseModel):
    raw_query: str


class DealQueryResponse(BaseModel):
    query_id: str


def _parse_query_id(query_id: str) -> int:
    try:
        return int(query_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deal query not found")


@router.post("/query", response_model=DealQueryResponse, status_code=202)
async def submit_deal_query(body: DealQueryRequest) -> DealQueryResponse:
    if not body.raw_query or not body.raw_query.strip():
        raise HTTPException(status_code=422, detail="raw_query must not be empty")

    query_id = create_deal_query(body.raw_query)
    asyncio.create_task(run_pipeline(query_id, body.raw_query))
    return DealQueryResponse(query_id=str(query_id))


@router.get("/{query_id}")
async def get_deal(query_id: str) -> dict:
    row = get_deal_query(_parse_query_id(query_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Deal query not found")
    return row["deal_state"] or {
        "query_id": query_id,
        "raw_query": row["raw_query"],
        "agent_trace": [],
        "retrieved_comps": [],
        "retrieved_clauses": [],
        "compliance_flags": [],
    }


@router.get("/{query_id}/trace")
async def get_deal_trace(query_id: str) -> dict:
    row = get_deal_query(_parse_query_id(query_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Deal query not found")
    return {"query_id": query_id, "agent_trace": row["agent_trace"] or []}


@router.get("/{query_id}/memo")
async def get_deal_memo(query_id: str, format: str = "json"):
    row = get_deal_query(_parse_query_id(query_id))
    if row is None or not row["deal_state"]:
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
    await websocket.accept()
    queue = await subscribe(query_id)
    try:
        row = get_deal_query(_parse_query_id(query_id)) if query_id.isdigit() else None
        if row and row["deal_state"]:
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

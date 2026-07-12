"""Canonical WS route per ARCHITECTURE.md Section 9: /ws/deals/{query_id}/stream."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.routers.deals import _stream_deal

router = APIRouter(tags=["ws"])


@router.websocket("/ws/deals/{query_id}/stream")
async def stream_deal(websocket: WebSocket, query_id: str):
    await _stream_deal(websocket, query_id)

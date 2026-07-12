"""In-process pub/sub bridging the (sync) LangGraph pipeline thread to the
WS endpoint's asyncio event loop. One asyncio.Queue per active query_id."""
from __future__ import annotations

import asyncio

_queues: dict[str, list[asyncio.Queue]] = {}
_lock = asyncio.Lock()


def _queues_for(query_id: str) -> list[asyncio.Queue]:
    return _queues.setdefault(query_id, [])


async def subscribe(query_id: str) -> asyncio.Queue:
    async with _lock:
        q: asyncio.Queue = asyncio.Queue()
        _queues_for(query_id).append(q)
        return q


async def unsubscribe(query_id: str, q: asyncio.Queue) -> None:
    async with _lock:
        subs = _queues_for(query_id)
        if q in subs:
            subs.remove(q)
        if not subs and query_id in _queues:
            del _queues[query_id]


def publish_threadsafe(loop: asyncio.AbstractEventLoop, query_id: str, message: dict) -> None:
    """Called from the worker thread running the LangGraph pipeline."""

    async def _put_all():
        for q in list(_queues_for(query_id)):
            await q.put(message)

    asyncio.run_coroutine_threadsafe(_put_all(), loop)

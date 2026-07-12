"""Pub/sub bridging the (sync) LangGraph pipeline thread to the WS
endpoint's asyncio event loop.

Two backends behind one interface:
  - Redis pub/sub, used when REDIS_URL is set. Required once the backend
    runs as more than one instance -- an in-memory dict only reaches
    subscribers connected to the same process, so a WS client connected to
    instance B never sees a "complete" event published by the worker thread
    on instance A.
  - An in-memory asyncio.Queue registry (the original implementation),
    used when REDIS_URL is unset. Fine for local dev and a single-instance
    deploy; this is the fallback, not the default recommendation.
"""
from __future__ import annotations

import asyncio
import json
import os

REDIS_URL = os.environ.get("REDIS_URL")


def _channel(query_id: str) -> str:
    return f"sakan:deal:{query_id}"


class Subscription:
    """Common interface both backends expose to callers: `await sub.get()`
    blocks for the next message, same shape as asyncio.Queue.get()."""

    async def get(self) -> dict:  # pragma: no cover - interface only
        raise NotImplementedError


# --- In-memory backend (fallback, single-instance only) ---

_queues: dict[str, list[asyncio.Queue]] = {}
_lock = asyncio.Lock()


def _queues_for(query_id: str) -> list[asyncio.Queue]:
    return _queues.setdefault(query_id, [])


class _InMemorySubscription(Subscription):
    def __init__(self, query_id: str, queue: asyncio.Queue):
        self.query_id = query_id
        self.queue = queue

    async def get(self) -> dict:
        return await self.queue.get()


async def _subscribe_in_memory(query_id: str) -> _InMemorySubscription:
    async with _lock:
        queue: asyncio.Queue = asyncio.Queue()
        _queues_for(query_id).append(queue)
        return _InMemorySubscription(query_id, queue)


async def _unsubscribe_in_memory(sub: _InMemorySubscription) -> None:
    async with _lock:
        subs = _queues_for(sub.query_id)
        if sub.queue in subs:
            subs.remove(sub.queue)
        if not subs and sub.query_id in _queues:
            del _queues[sub.query_id]


def _publish_in_memory(loop: asyncio.AbstractEventLoop, query_id: str, message: dict) -> None:
    async def _put_all():
        for q in list(_queues_for(query_id)):
            await q.put(message)

    asyncio.run_coroutine_threadsafe(_put_all(), loop)


# --- Redis backend (multi-instance safe) ---

_redis_sync_client = None  # lazily constructed; safe to call .publish() from any thread


def _get_sync_redis_client():
    global _redis_sync_client
    if _redis_sync_client is None:
        import redis as redis_sync

        _redis_sync_client = redis_sync.Redis.from_url(REDIS_URL)
    return _redis_sync_client


class _RedisSubscription(Subscription):
    def __init__(self, query_id: str, client, pubsub):
        self.query_id = query_id
        self._client = client
        self._pubsub = pubsub
        self._messages = pubsub.listen()

    async def get(self) -> dict:
        async for raw in self._messages:
            if raw["type"] == "message":
                return json.loads(raw["data"])
        raise RuntimeError("Redis pub/sub connection closed unexpectedly")  # pragma: no cover


async def _subscribe_redis(query_id: str) -> _RedisSubscription:
    import redis.asyncio as redis_async

    client = redis_async.Redis.from_url(REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel(query_id))
    return _RedisSubscription(query_id, client, pubsub)


async def _unsubscribe_redis(sub: _RedisSubscription) -> None:
    await sub._pubsub.unsubscribe(_channel(sub.query_id))
    await sub._pubsub.aclose()
    await sub._client.aclose()


def _publish_redis(query_id: str, message: dict) -> None:
    _get_sync_redis_client().publish(_channel(query_id), json.dumps(message))


# --- Public interface ---


async def subscribe(query_id: str) -> Subscription:
    if REDIS_URL:
        return await _subscribe_redis(query_id)
    return await _subscribe_in_memory(query_id)


async def unsubscribe(query_id: str, sub: Subscription) -> None:
    if isinstance(sub, _RedisSubscription):
        await _unsubscribe_redis(sub)
    else:
        await _unsubscribe_in_memory(sub)


def publish_threadsafe(loop: asyncio.AbstractEventLoop, query_id: str, message: dict) -> None:
    """Called from the worker thread running the LangGraph pipeline."""
    if REDIS_URL:
        _publish_redis(query_id, message)  # redis-py sync client is thread-safe to call directly
    else:
        _publish_in_memory(loop, query_id, message)

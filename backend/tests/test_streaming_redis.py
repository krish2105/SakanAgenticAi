"""Exercises the Redis-backed pub/sub path against a real local Redis
instance -- REDIS_URL being set is exactly the case the in-memory fallback
tests (elsewhere, via the WS tests in test_api.py) don't cover, and it's the
whole point of this backend existing (multi-instance WS fanout)."""
import asyncio

import pytest

import app.streaming as streaming_module

REDIS_URL = "redis://localhost:6379/0"


def _redis_available() -> bool:
    try:
        import redis

        redis.Redis.from_url(REDIS_URL).ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_available(), reason="no local Redis instance to test against")


def test_redis_pubsub_delivers_a_published_message(monkeypatch):
    monkeypatch.setattr(streaming_module, "REDIS_URL", REDIS_URL)
    monkeypatch.setattr(streaming_module, "_redis_sync_client", None)

    async def run():
        sub = await streaming_module.subscribe("redis-test-basic")
        try:
            loop = asyncio.get_running_loop()
            await asyncio.to_thread(
                streaming_module.publish_threadsafe, loop, "redis-test-basic", {"type": "state", "data": {"x": 1}}
            )
            message = await asyncio.wait_for(sub.get(), timeout=5)
            assert message == {"type": "state", "data": {"x": 1}}
        finally:
            await streaming_module.unsubscribe("redis-test-basic", sub)

    asyncio.run(run())


def test_redis_pubsub_fans_out_to_multiple_subscribers(monkeypatch):
    """This is the actual scaling property the migration is for: two
    subscribers to the same query_id -- standing in for two WS clients
    connected to two different backend instances -- both get the message
    published by a single publish_threadsafe call."""
    monkeypatch.setattr(streaming_module, "REDIS_URL", REDIS_URL)
    monkeypatch.setattr(streaming_module, "_redis_sync_client", None)

    async def run():
        sub_a = await streaming_module.subscribe("redis-test-fanout")
        sub_b = await streaming_module.subscribe("redis-test-fanout")
        try:
            loop = asyncio.get_running_loop()
            await asyncio.to_thread(
                streaming_module.publish_threadsafe,
                loop,
                "redis-test-fanout",
                {"type": "complete", "data": {"done": True}},
            )
            msg_a = await asyncio.wait_for(sub_a.get(), timeout=5)
            msg_b = await asyncio.wait_for(sub_b.get(), timeout=5)
            assert msg_a == {"type": "complete", "data": {"done": True}}
            assert msg_b == {"type": "complete", "data": {"done": True}}
        finally:
            await streaming_module.unsubscribe("redis-test-fanout", sub_a)
            await streaming_module.unsubscribe("redis-test-fanout", sub_b)

    asyncio.run(run())


def test_in_memory_fallback_used_when_redis_url_unset(monkeypatch):
    monkeypatch.setattr(streaming_module, "REDIS_URL", None)

    async def run():
        sub = await streaming_module.subscribe("mem-test-1")
        assert isinstance(sub, streaming_module._InMemorySubscription)
        await streaming_module.unsubscribe("mem-test-1", sub)

    asyncio.run(run())

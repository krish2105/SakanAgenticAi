"""Unit tests for app/cache.py: in-memory TTL behavior (default, no
REDIS_URL) and the Redis-backed path (mocked), including that a cache miss
or Redis error always falls through to a live call rather than erroring."""
import asyncio

import pytest

import app.cache as cache_module


@pytest.fixture(autouse=True)
def _clear_memory_cache():
    cache_module._memory_cache.clear()
    yield
    cache_module._memory_cache.clear()


def test_in_memory_cache_returns_cached_value_without_recalling(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_URL", None)
    calls = []

    @cache_module.cached(ttl_seconds=60)
    async def compute(x: int) -> dict:
        calls.append(x)
        return {"x": x}

    result1 = asyncio.run(compute(5))
    result2 = asyncio.run(compute(5))

    assert result1 == {"x": 5}
    assert result2 == {"x": 5}
    assert calls == [5]  # second call served from cache, not recomputed


def test_in_memory_cache_distinguishes_different_args(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_URL", None)
    calls = []

    @cache_module.cached(ttl_seconds=60)
    async def compute(x: int) -> dict:
        calls.append(x)
        return {"x": x}

    asyncio.run(compute(1))
    asyncio.run(compute(2))

    assert calls == [1, 2]


def test_in_memory_cache_expires_after_ttl(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_URL", None)
    fake_time = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_time[0])
    calls = []

    @cache_module.cached(ttl_seconds=10)
    async def compute() -> dict:
        calls.append(1)
        return {"n": len(calls)}

    asyncio.run(compute())
    fake_time[0] += 11  # past the 10s TTL
    asyncio.run(compute())

    assert calls == [1, 1]  # recomputed after expiry


def test_redis_cache_hit_avoids_recompute(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_URL", "redis://fake")
    calls = []
    store: dict[str, str] = {}

    class _FakeRedis:
        def get(self, key):
            return store.get(key)

        def setex(self, key, ttl, value):
            store[key] = value

    monkeypatch.setattr(cache_module, "_redis_client", lambda: _FakeRedis())

    @cache_module.cached(ttl_seconds=30)
    async def compute() -> dict:
        calls.append(1)
        return {"n": len(calls)}

    result1 = asyncio.run(compute())
    result2 = asyncio.run(compute())

    assert result1 == {"n": 1}
    assert result2 == {"n": 1}  # served from the fake Redis store, not recomputed
    assert calls == [1]


def test_redis_read_error_falls_through_to_live_call(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_URL", "redis://fake")

    class _BrokenRedis:
        def get(self, key):
            raise ConnectionError("redis unreachable")

        def setex(self, key, ttl, value):
            raise ConnectionError("redis unreachable")

    monkeypatch.setattr(cache_module, "_redis_client", lambda: _BrokenRedis())

    @cache_module.cached(ttl_seconds=30)
    async def compute() -> dict:
        return {"ok": True}

    # Must not raise even though every Redis call fails.
    assert asyncio.run(compute()) == {"ok": True}

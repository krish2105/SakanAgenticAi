"""Lightweight cache for read-heavy, expensive-to-recompute endpoints
(market ticker/trends, comps search) -- none of these had any caching before
this, so every request recomputed a Postgres GROUP BY/ORDER BY aggregate
from scratch.

Redis-backed when REDIS_URL is set, reusing the same sync client
app/streaming.py already maintains for pub/sub (not duplicated here), so a
cache warmed by one instance is visible to all instances. Falls back to a
process-local in-memory dict with the same TTL semantics when REDIS_URL is
unset -- fine for a single free-tier instance, the same fallback pattern
streaming.py already uses for pub/sub.
"""
from __future__ import annotations

import functools
import json
import logging
import time
from collections.abc import Callable

from app.streaming import REDIS_URL

log = logging.getLogger("sakan.cache")

_CACHE_PREFIX = "sakan:cache:"
_memory_cache: dict[str, tuple[float, object]] = {}


def _redis_client():
    from app.streaming import _get_sync_redis_client

    return _get_sync_redis_client()


def _make_key(name: str, args: tuple, kwargs: dict) -> str:
    parts = [name, *[repr(a) for a in args], *[f"{k}={v!r}" for k, v in sorted(kwargs.items())]]
    return _CACHE_PREFIX + "|".join(parts)


def cached(ttl_seconds: int):
    """Decorator for async route handlers returning JSON-serializable data.
    Cache key is the function name plus every positional/keyword arg it was
    called with, so different filters/params never collide."""

    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = _make_key(fn.__name__, args, kwargs)

            if REDIS_URL:
                try:
                    cached_value = _redis_client().get(key)
                    if cached_value is not None:
                        return json.loads(cached_value)
                except Exception:  # noqa: BLE001
                    log.warning("Cache read failed for %s; falling through to a live query.", key)
            else:
                entry = _memory_cache.get(key)
                if entry is not None and entry[0] > time.monotonic():
                    return entry[1]

            result = await fn(*args, **kwargs)

            if REDIS_URL:
                try:
                    _redis_client().setex(key, ttl_seconds, json.dumps(result))
                except Exception:  # noqa: BLE001
                    log.warning("Cache write failed for %s; result still returned uncached.", key)
            else:
                _memory_cache[key] = (time.monotonic() + ttl_seconds, result)

            return result

        return wrapper

    return decorator

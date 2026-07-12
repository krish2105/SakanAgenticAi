"""Shared slowapi limiter + a proxy-aware key function.

One limiter instance is registered on app.state (main.py) and imported by every
router that needs limits (deals, auth), so limits key consistently and the
RateLimitExceeded handler catches them all.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip_key(request: Request) -> str:
    """Rate-limit key that survives Render's (and most PaaS) reverse proxy.

    slowapi's default get_remote_address reads request.client.host, which behind
    a proxy is the *proxy's* IP -- so every user shares one bucket. The real
    client is the left-most entry of X-Forwarded-For. Falls back to the socket
    address when the header is absent (local/dev)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip_key)

"""Cloudflare Turnstile bot-challenge verification (Phase 16).

Optional: verify_turnstile_token accepts every token (returns True) when
TURNSTILE_SECRET_KEY is unset, same no-op-when-unconfigured pattern as
email/analytics/Stripe elsewhere in this app -- register/login work
identically without it, just without the bot challenge.
"""
from __future__ import annotations

import logging

import httpx

from app import config

log = logging.getLogger("sakan.turnstile")

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str | None, remote_ip: str | None = None) -> bool:
    if not config.TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False

    payload = {"secret": config.TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.post(SITEVERIFY_URL, data=payload)
            res.raise_for_status()
            body = res.json()
            return bool(body.get("success"))
    except Exception:  # noqa: BLE001
        # A Cloudflare outage or network hiccup shouldn't lock every user out
        # of registering/logging in -- log it and fail open, same posture as
        # this app's other best-effort external calls (e.g. team_service's
        # Stripe seat sync).
        log.exception("Turnstile verification request failed; failing open")
        return True

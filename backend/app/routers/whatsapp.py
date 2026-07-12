"""WhatsApp Business Cloud API integration (Phase C of the MVP roadmap:
"~70% of real Dubai property inquiries arrive over WhatsApp; a
query-by-WhatsApp flow meets agents where they already work").

Never verified against a real Meta/WhatsApp Business account -- this
sandbox has no such credentials. The webhook handshake, signature
verification, and payload parsing follow Meta's publicly documented Cloud
API contract and are covered by tests using a hand-built fixture payload
matching that documented shape; the actual send-message call to
graph.facebook.com has never round-tripped against Meta's servers.

Design: a message from an unrecognized phone number gets a pseudo-account
auto-provisioned for it (email `whatsapp+<number>@sakan.internal`, an
unusable random password) rather than requiring a WhatsApp user to sign up
through the web app first -- that's the whole point of meeting agents
where they already work. That pseudo-account still goes through the same
billing_service quota as everyone else, so a WhatsApp user gets the same
Starter-tier monthly limit by construction, no special-casing needed.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app import config
from app.auth import hash_password
from app.db import get_session_factory
from app.models import User
from app.services.billing_service import enforce_quota
from app.services.pipeline_runner import create_deal_query, ensure_tables, run_pipeline
from app.streaming import subscribe, unsubscribe

log = logging.getLogger("sakan.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    """Meta's one-time webhook subscription handshake: GET with
    hub.mode=subscribe and a token that must match WHATSAPP_VERIFY_TOKEN;
    echo hub.challenge back verbatim to confirm ownership."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and config.WHATSAPP_VERIFY_TOKEN and token == config.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """Meta signs each webhook POST with X-Hub-Signature-256 (HMAC-SHA256
    over the raw body, keyed by the app secret). No WHATSAPP_APP_SECRET
    configured means accept unverified -- dev-only fallback, same posture
    as the Stripe webhook's unverified path; every production deployment
    MUST set WHATSAPP_APP_SECRET."""
    if not config.WHATSAPP_APP_SECRET:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(config.WHATSAPP_APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    provided = signature_header[len("sha256=") :]
    return hmac.compare_digest(expected, provided)


def extract_messages(payload: dict) -> list[dict]:
    """Returns [{"from": wa_id, "text": body}, ...] for every inbound text
    message in a webhook payload. Meta's payload can also carry delivery/
    read status callbacks and non-text message types (image, location,
    template replies) in the same shape under "changes" -- those are
    silently skipped, not an oversight: this integration answers a typed
    question, not a general WhatsApp inbox."""
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") == "text" and msg.get("text", {}).get("body"):
                    out.append({"from": msg["from"], "text": msg["text"]["body"]})
    return out


def get_or_create_whatsapp_user(session, phone_number: str) -> User:
    pseudo_email = f"whatsapp+{phone_number}@sakan.internal"
    user = session.scalar(select(User).where(User.email == pseudo_email))
    if user is not None:
        return user

    user = User(
        email=pseudo_email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        full_name=None,
        role="Agent",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


async def send_whatsapp_message(to: str, body: str) -> None:
    """No-ops with a log line (not an exception) when WhatsApp isn't
    configured -- a webhook handler racing a missing outbound credential
    shouldn't 500, it should just not send anything."""
    if not (config.WHATSAPP_ACCESS_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID):
        log.info("WhatsApp send skipped (not configured) -- would have sent to %s: %s", to, body)
        return

    import httpx

    url = f"https://graph.facebook.com/v20.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}
    body_payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": body}}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=body_payload, headers=headers)
            if res.status_code >= 400:
                log.warning("WhatsApp send failed (%s): %s", res.status_code, res.text)
    except Exception:  # noqa: BLE001
        log.exception("WhatsApp send raised for %s", to)


def format_reply(state: dict) -> str:
    lines = []
    if state.get("valuation_low") is not None and state.get("valuation_high") is not None:
        lines.append(f"Estimated range: AED {state['valuation_low']:,.0f} - {state['valuation_high']:,.0f}")
    if state.get("compliance_summary"):
        lines.append(f"Compliance: {state['compliance_summary'][:300]}")
    if not lines:
        lines.append("No result available for this query.")
    lines.append("Full memo and citations: see the Sakan AI web app (WhatsApp replies are summary-only).")
    return "\n\n".join(lines)


async def _notify_when_ready(query_id: str, to_phone_number: str) -> None:
    sub = await subscribe(query_id)
    try:
        while True:
            message = await sub.get()
            msg_type = message.get("type")
            if msg_type == "complete":
                await send_whatsapp_message(to_phone_number, format_reply(message.get("data") or {}))
                return
            if msg_type == "error":
                await send_whatsapp_message(to_phone_number, "Sorry, something went wrong processing that query.")
                return
    finally:
        await unsubscribe(query_id, sub)


@router.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    payload_bytes = await request.body()
    if not verify_signature(payload_bytes, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    messages = extract_messages(payload)
    if messages:
        ensure_tables()

    session_factory = get_session_factory()
    for msg in messages:
        with session_factory() as session:
            user = get_or_create_whatsapp_user(session, msg["from"])
            try:
                enforce_quota(session, user)
            except HTTPException:
                asyncio.create_task(
                    send_whatsapp_message(
                        msg["from"],
                        "You've reached this month's free query limit. Upgrade at the Sakan AI web app to continue.",
                    )
                )
                continue
            owner_id = user.user_id

        query_id = create_deal_query(msg["text"], owner_id=owner_id)
        asyncio.create_task(run_pipeline(query_id, msg["text"]))
        asyncio.create_task(_notify_when_ready(str(query_id), msg["from"]))

    return {"received": True}

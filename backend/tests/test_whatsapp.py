"""Tests for app/routers/whatsapp.py.

Never verified against a real Meta/WhatsApp Business account (no
credentials available in this sandbox) -- these tests cover the parts that
don't need one: the webhook handshake, signature verification, payload
parsing against a hand-built fixture matching Meta's documented Cloud API
shape, user auto-provisioning, and quota enforcement. send_whatsapp_message
is monkeypatched wherever a test needs to observe whether it *would* have
been called, since the real one only no-ops (logs) without credentials.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.routers.whatsapp as whatsapp_module
from app.db import get_session_factory
from app.main import app
from app.models import DealQuery, User

SAMPLE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "15550001111", "phone_number_id": "999"},
                        "contacts": [{"profile": {"name": "Test User"}, "wa_id": "971501234567"}],
                        "messages": [
                            {
                                "from": "971501234567",
                                "id": "wamid.abc123",
                                "timestamp": "1700000000",
                                "text": {"body": "2BR apartment in Dubai Marina under 2.2M"},
                                "type": "text",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

STATUS_CALLBACK_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "15550001111", "phone_number_id": "999"},
                        "statuses": [{"id": "wamid.abc123", "status": "delivered"}],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


def test_webhook_verification_succeeds_with_correct_token(monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_VERIFY_TOKEN", "my-verify-token")
    with TestClient(app) as client:
        res = client.get(
            "/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "my-verify-token", "hub.challenge": "echo-me-123"},
        )
        assert res.status_code == 200
        assert res.text == "echo-me-123"


def test_webhook_verification_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_VERIFY_TOKEN", "my-verify-token")
    with TestClient(app) as client:
        res = client.get(
            "/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "echo-me-123"},
        )
        assert res.status_code == 403


def test_verify_signature_accepts_unverified_when_no_secret_configured(monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_APP_SECRET", None)
    assert whatsapp_module.verify_signature(b"anything", None) is True


def test_verify_signature_checks_hmac_when_secret_configured(monkeypatch):
    import hashlib
    import hmac

    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_APP_SECRET", "shh")
    body = b'{"object": "whatsapp_business_account"}'
    valid_sig = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()

    assert whatsapp_module.verify_signature(body, valid_sig) is True
    assert whatsapp_module.verify_signature(body, "sha256=deadbeef") is False
    assert whatsapp_module.verify_signature(body, None) is False


def test_extract_messages_parses_text_messages():
    messages = whatsapp_module.extract_messages(SAMPLE_PAYLOAD)
    assert messages == [{"from": "971501234567", "text": "2BR apartment in Dubai Marina under 2.2M"}]


def test_extract_messages_ignores_status_callbacks():
    assert whatsapp_module.extract_messages(STATUS_CALLBACK_PAYLOAD) == []


def test_get_or_create_whatsapp_user_reuses_existing_pseudo_account(seeded_sqlite_db):
    from app.db import get_engine
    from app.services.pipeline_runner import ensure_tables

    ensure_tables()
    engine = get_engine(seeded_sqlite_db)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        first = whatsapp_module.get_or_create_whatsapp_user(session, "971501234567")
        second = whatsapp_module.get_or_create_whatsapp_user(session, "971501234567")
        assert first.user_id == second.user_id
        assert first.email == "whatsapp+971501234567@sakan.internal"


def test_send_whatsapp_message_noop_without_credentials(monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_ACCESS_TOKEN", None)
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_PHONE_NUMBER_ID", None)

    called = []

    class ExplodingClient:
        def __init__(self, *a, **k):
            called.append(True)

    monkeypatch.setattr("httpx.AsyncClient", ExplodingClient)

    import asyncio

    asyncio.run(whatsapp_module.send_whatsapp_message("971501234567", "hello"))
    assert called == []  # never even tried to construct an HTTP client


def test_receive_webhook_creates_a_deal_query_for_a_new_phone_number(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_APP_SECRET", None)

    with TestClient(app) as client:
        res = client.post("/whatsapp/webhook", json=SAMPLE_PAYLOAD)
        assert res.status_code == 200

        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "whatsapp+971501234567@sakan.internal"))
            assert user is not None
            deal = session.scalar(select(DealQuery).where(DealQuery.owner_id == user.user_id))
            assert deal is not None
            assert deal.raw_query == "2BR apartment in Dubai Marina under 2.2M"


def test_receive_webhook_rejects_bad_signature(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_APP_SECRET", "shh")
    with TestClient(app) as client:
        res = client.post(
            "/whatsapp/webhook",
            json=SAMPLE_PAYLOAD,
            headers={"x-hub-signature-256": "sha256=deadbeef"},
        )
        assert res.status_code == 403


def test_receive_webhook_stops_creating_deal_queries_past_the_quota(seeded_sqlite_db, monkeypatch):
    # Not asserting on the "you've hit your limit" WhatsApp reply here --
    # it's sent via a fire-and-forget asyncio.create_task, which isn't
    # guaranteed to have run by the time TestClient.post() returns, and
    # this test doesn't need it: the row count is the property that
    # actually matters (quota enforcement, not the notification copy).
    monkeypatch.setattr(whatsapp_module.config, "WHATSAPP_APP_SECRET", None)

    with TestClient(app) as client:
        for _ in range(6):
            res = client.post("/whatsapp/webhook", json=SAMPLE_PAYLOAD)
            assert res.status_code == 200

        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "whatsapp+971501234567@sakan.internal"))
            deal_count = len(session.scalars(select(DealQuery).where(DealQuery.owner_id == user.user_id)).all())

        # Starter tier defaults to 5 full-pipeline queries/month.
        assert deal_count == 5

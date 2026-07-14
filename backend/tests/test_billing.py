"""Tests for app/routers/billing.py and app/services/billing_service.py.

Never verified against a real Stripe account (no network path to
api.stripe.com from this sandbox) -- checkout/portal/webhook tests
monkeypatch the `stripe` SDK calls instead, which covers our own wiring
(customer creation, DB updates, tier mapping) but not Stripe's own API
behavior.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.routers.billing as billing_module
from app.db import get_session_factory
from app.main import app
from app.models import User
from app.routers.deals import limiter


def _register(client: TestClient, email: str) -> dict:
    res = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_plans_lists_all_four_tiers(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/billing/plans")
        assert res.status_code == 200
        plans = res.json()
        assert set(plans) == {"starter", "pro", "team", "enterprise"}
        assert plans["starter"]["monthly_query_limit"] == 5
        assert plans["starter"]["price_aed_monthly"] == 0
        assert plans["pro"]["self_serve_checkout"] is True
        assert plans["enterprise"]["self_serve_checkout"] is False


def test_billing_me_reports_starter_defaults(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "billing-me@example.com")
        res = client.get("/billing/me", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert body["tier"] == "starter"
        assert body["monthly_query_limit"] == 5
        assert body["queries_used_this_month"] == 0
        assert body["queries_remaining"] == 5


def test_usage_timeseries_requires_auth(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/billing/usage-timeseries").status_code == 401


def test_usage_timeseries_reflects_queries_submitted_today(seeded_sqlite_db):
    limiter.reset()
    try:
        with TestClient(app) as client:
            headers = _register(client, "usage-timeseries@example.com")

            empty = client.get("/billing/usage-timeseries", headers=headers)
            assert empty.status_code == 200
            assert empty.json() == {"days": []}

            for i in range(3):
                res = client.post("/deals/query", json={"raw_query": f"usage query {i}"}, headers=headers)
                assert res.status_code == 202

            after = client.get("/billing/usage-timeseries", headers=headers).json()
            assert len(after["days"]) == 1  # all 3 queries land on today's date
            assert after["days"][0]["count"] == 3
    finally:
        limiter.reset()


def test_starter_tier_is_blocked_after_five_full_pipeline_queries(seeded_sqlite_db):
    limiter.reset()
    try:
        with TestClient(app) as client:
            headers = _register(client, "quota@example.com")

            statuses = [
                client.post("/deals/query", json={"raw_query": f"query {i}"}, headers=headers).status_code
                for i in range(6)
            ]
            assert statuses == [202, 202, 202, 202, 202, 402]

            me = client.get("/billing/me", headers=headers).json()
            assert me["queries_used_this_month"] == 5
            assert me["queries_remaining"] == 0
    finally:
        limiter.reset()


def test_pro_tier_has_no_quota_at_five_queries(seeded_sqlite_db):
    limiter.reset()
    try:
        with TestClient(app) as client:
            headers = _register(client, "pro-quota@example.com")

            session_factory = get_session_factory()
            with session_factory() as session:
                user = session.scalar(select(User).where(User.email == "pro-quota@example.com"))
                user.tier = "pro"
                session.add(user)
                session.commit()

            statuses = [
                client.post("/deals/query", json={"raw_query": f"query {i}"}, headers=headers).status_code
                for i in range(6)
            ]
            assert statuses == [202] * 6
    finally:
        limiter.reset()


def test_checkout_returns_501_when_stripe_not_configured(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", None)
    with TestClient(app) as client:
        headers = _register(client, "no-stripe@example.com")
        res = client.post("/billing/checkout", json={"tier": "pro"}, headers=headers)
        assert res.status_code == 501


def test_checkout_returns_501_when_price_id_not_configured(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_PRICE_ID_PRO", None)
    with TestClient(app) as client:
        headers = _register(client, "no-price@example.com")
        res = client.post("/billing/checkout", json={"tier": "pro"}, headers=headers)
        assert res.status_code == 501


def test_checkout_creates_stripe_customer_and_session(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_PRICE_ID_PRO", "price_pro_fake")

    created_customers = []
    created_sessions = []

    def fake_customer_create(email, metadata):
        created_customers.append((email, metadata))
        return {"id": "cus_fake123"}

    def fake_checkout_create(**kwargs):
        created_sessions.append(kwargs)
        return {"url": "https://checkout.stripe.com/fake-session"}

    monkeypatch.setattr(billing_module.stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(billing_module.stripe.checkout.Session, "create", fake_checkout_create)

    with TestClient(app) as client:
        headers = _register(client, "checkout@example.com")
        res = client.post("/billing/checkout", json={"tier": "pro"}, headers=headers)

        assert res.status_code == 200
        assert res.json()["checkout_url"] == "https://checkout.stripe.com/fake-session"
        assert created_customers[0][0] == "checkout@example.com"
        assert created_sessions[0]["customer"] == "cus_fake123"
        assert created_sessions[0]["line_items"][0]["price"] == "price_pro_fake"

        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "checkout@example.com"))
            assert user.stripe_customer_id == "cus_fake123"

        # A second checkout call must reuse the existing Stripe customer, not create another.
        client.post("/billing/checkout", json={"tier": "pro"}, headers=headers)
        assert len(created_customers) == 1


def test_webhook_subscription_updated_upgrades_tier(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)  # unverified path for this test
    monkeypatch.setattr(billing_module.config, "STRIPE_PRICE_ID_PRO", "price_pro_fake")

    with TestClient(app) as client:
        _register(client, "webhook-user@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "webhook-user@example.com"))
            user.stripe_customer_id = "cus_webhook_test"
            session.add(user)
            session.commit()

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_fake",
                    "customer": "cus_webhook_test",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_pro_fake"}}]},
                }
            },
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "webhook-user@example.com"))
            assert user.tier == "pro"
            assert user.subscription_status == "active"
            assert user.stripe_subscription_id == "sub_fake"


def test_webhook_subscription_deleted_downgrades_to_starter(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)

    with TestClient(app) as client:
        _register(client, "cancel-user@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "cancel-user@example.com"))
            user.stripe_customer_id = "cus_cancel_test"
            user.tier = "pro"
            user.subscription_status = "active"
            session.add(user)
            session.commit()

        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_cancel_test"}},
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "cancel-user@example.com"))
            assert user.tier == "starter"
            assert user.subscription_status == "canceled"


def test_webhook_rejects_invalid_signature(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", "whsec_fake")

    def fake_construct_event(payload, sig_header, secret):
        raise billing_module.stripe.error.SignatureVerificationError("bad signature", sig_header)

    monkeypatch.setattr(billing_module.stripe.Webhook, "construct_event", fake_construct_event)

    with TestClient(app) as client:
        res = client.post(
            "/billing/webhook",
            json={"type": "customer.subscription.updated", "data": {"object": {}}},
            headers={"stripe-signature": "bad"},
        )
        assert res.status_code == 400


def test_webhook_replayed_event_is_not_reapplied(seeded_sqlite_db, monkeypatch):
    """Phase 11a: Stripe can redeliver the same event id more than once --
    a replay must be a no-op, not a second tier upgrade / second email."""
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)
    monkeypatch.setattr(billing_module.config, "STRIPE_PRICE_ID_PRO", "price_pro_fake")

    with TestClient(app) as client:
        _register(client, "replay-user@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "replay-user@example.com"))
            user.stripe_customer_id = "cus_replay_test"
            session.add(user)
            session.commit()

        event = {
            "id": "evt_replay_test",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_replay",
                    "customer": "cus_replay_test",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_pro_fake"}}]},
                }
            },
        }
        first = client.post("/billing/webhook", json=event)
        assert first.status_code == 200
        assert first.json() == {"received": True}

        second = client.post("/billing/webhook", json=event)
        assert second.status_code == 200
        assert second.json() == {"received": True, "duplicate": True}

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "replay-user@example.com"))
            assert user.tier == "pro"  # applied exactly once, not corrupted by the replay


def test_webhook_payment_failed_flags_past_due_and_emails_user(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)

    sent_emails = []
    monkeypatch.setattr(
        billing_module,
        "send_email",
        lambda to, subject, body: sent_emails.append((to, subject, body)),
    )

    with TestClient(app) as client:
        _register(client, "dunning-user@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "dunning-user@example.com"))
            user.stripe_customer_id = "cus_dunning_test"
            user.tier = "pro"
            user.subscription_status = "active"
            session.add(user)
            session.commit()

        event = {
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_dunning_test"}},
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "dunning-user@example.com"))
            assert user.subscription_status == "past_due"
            assert user.tier == "pro"  # not downgraded -- Stripe's own retries govern that

        assert len(sent_emails) == 1
        assert sent_emails[0][0] == "dunning-user@example.com"
        assert "payment failed" in sent_emails[0][1].lower()


def test_webhook_payment_succeeded_recovers_past_due(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)

    with TestClient(app) as client:
        _register(client, "recovered-user@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "recovered-user@example.com"))
            user.stripe_customer_id = "cus_recovered_test"
            user.subscription_status = "past_due"
            session.add(user)
            session.commit()

        event = {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"customer": "cus_recovered_test"}},
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "recovered-user@example.com"))
            assert user.subscription_status == "active"


def test_webhook_payment_succeeded_ignores_routine_renewal(seeded_sqlite_db, monkeypatch):
    """A normal monthly renewal invoice also fires payment_succeeded -- it
    must not touch a user who was never past_due (e.g. flip "active" to
    "active" pointlessly, or worse, overwrite some other status)."""
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)

    with TestClient(app) as client:
        _register(client, "routine-user@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "routine-user@example.com"))
            user.stripe_customer_id = "cus_routine_test"
            user.subscription_status = "canceled"
            session.add(user)
            session.commit()

        event = {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"customer": "cus_routine_test"}},
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "routine-user@example.com"))
            assert user.subscription_status == "canceled"  # untouched

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
        headers = _register(client, "webhook-user@example.com")

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
        headers = _register(client, "cancel-user@example.com")

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

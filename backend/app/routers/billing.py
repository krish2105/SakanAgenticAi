"""Stripe checkout/portal/webhook + plan and quota endpoints (Phase B).

Every Stripe-touching endpoint checks `config.STRIPE_SECRET_KEY` at call
time (via the `config` module object, not an import-time constant) so it
degrades to a clear 501 instead of crashing when no Stripe account is
configured yet -- same fallback posture as ANTHROPIC_API_KEY elsewhere in
this app. Never verified against a real Stripe account from this sandbox
(no network path to api.stripe.com here); the webhook handler and checkout
flow are covered by tests that monkeypatch the `stripe` SDK calls.
"""
from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.auth import get_current_user
from app.db import get_session_factory
from app.models import User
from app.services.billing_service import PLANS, quota_status, stripe_price_id_for, tier_for_price_id
from app.services.pipeline_runner import ensure_tables

log = logging.getLogger("sakan.billing")

router = APIRouter(prefix="/billing", tags=["billing"])

_CHECKOUT_TIERS = {"pro", "team"}  # Starter is free (no Checkout); Enterprise is contact-sales.


class CheckoutRequest(BaseModel):
    tier: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


def _require_stripe_configured() -> None:
    if not config.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=501,
            detail="Billing is not configured on this deployment (STRIPE_SECRET_KEY unset).",
        )
    stripe.api_key = config.STRIPE_SECRET_KEY


@router.get("/plans")
async def list_plans() -> dict:
    return {
        tier: {
            "label": plan["label"],
            "price_aed_monthly": plan["price_aed_monthly"],
            "monthly_query_limit": plan["monthly_query_limit"],
            "self_serve_checkout": tier in _CHECKOUT_TIERS,
        }
        for tier, plan in PLANS.items()
    }


@router.get("/me")
async def billing_me(current_user: User = Depends(get_current_user)) -> dict:
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        return quota_status(session, current_user)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest, current_user: User = Depends(get_current_user)
) -> CheckoutResponse:
    if body.tier not in _CHECKOUT_TIERS:
        raise HTTPException(status_code=422, detail=f"tier must be one of {sorted(_CHECKOUT_TIERS)}")
    _require_stripe_configured()

    price_id = stripe_price_id_for(body.tier)
    if not price_id:
        raise HTTPException(
            status_code=501,
            detail=f"No Stripe price configured for the {body.tier} tier "
            f"(set STRIPE_PRICE_ID_{body.tier.upper()}).",
        )

    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, current_user.user_id)
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.user_id)})
            customer_id = customer["id"]
            user.stripe_customer_id = customer_id
            session.add(user)
            session.commit()

    checkout_session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(current_user.user_id),
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{config.FRONTEND_URL}/billing?checkout=success",
        cancel_url=f"{config.FRONTEND_URL}/billing?checkout=cancelled",
    )
    return CheckoutResponse(checkout_url=checkout_session["url"])


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(current_user: User = Depends(get_current_user)) -> PortalResponse:
    _require_stripe_configured()
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account found for this user yet.")

    portal_session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{config.FRONTEND_URL}/billing",
    )
    return PortalResponse(portal_url=portal_session["url"])


def _apply_subscription_to_user(session, *, customer_id: str, subscription_id: str | None, price_id: str | None, status: str) -> None:
    from sqlalchemy import select

    user = session.scalar(select(User).where(User.stripe_customer_id == customer_id))
    if user is None:
        log.warning("Stripe webhook for unknown customer_id=%s", customer_id)
        return

    user.stripe_subscription_id = subscription_id
    user.subscription_status = status
    if status in ("active", "trialing"):
        tier = tier_for_price_id(price_id)
        if tier:
            user.tier = tier
    elif status in ("canceled", "unpaid", "incomplete_expired"):
        user.tier = "starter"
    session.add(user)
    session.commit()


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    _require_stripe_configured()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        if config.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)
        elif config.IS_PRODUCTION:
            # Fail closed: an unsigned event in production could forge a
            # subscription upgrade. config._validate_production_config already
            # blocks boot in this state, but refuse here too as defense in depth.
            raise HTTPException(
                status_code=400,
                detail="STRIPE_WEBHOOK_SECRET is required in production; refusing unsigned webhook.",
            )
        else:
            # No webhook secret configured -- accept unverified in dev only.
            import json

            event = json.loads(payload)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}")

    event_type = event["type"]
    data = event["data"]["object"]
    session_factory = get_session_factory()

    if event_type == "checkout.session.completed":
        with session_factory() as session:
            _apply_subscription_to_user(
                session,
                customer_id=data["customer"],
                subscription_id=data.get("subscription"),
                price_id=None,  # subscription.updated (fired right after) carries the price id
                status="active",
            )
    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        price_id = data["items"]["data"][0]["price"]["id"] if data.get("items", {}).get("data") else None
        with session_factory() as session:
            _apply_subscription_to_user(
                session,
                customer_id=data["customer"],
                subscription_id=data["id"],
                price_id=price_id,
                status=data["status"],
            )
    elif event_type == "customer.subscription.deleted":
        with session_factory() as session:
            _apply_subscription_to_user(
                session,
                customer_id=data["customer"],
                subscription_id=None,
                price_id=None,
                status="canceled",
            )
    else:
        log.info("Unhandled Stripe webhook event type: %s", event_type)

    return {"received": True}

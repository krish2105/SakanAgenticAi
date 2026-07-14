"""Phase 11c -- team/seat billing: Organization creation, invite/accept,
membership listing, and removal. Stripe seat-quantity sync is exercised
separately (mocked) since it's best-effort and shouldn't block membership
changes even when it fails.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.routers.billing as billing_module
from app.db import get_session_factory
from app.main import app
from app.models import Organization, User
from app.services import team_service


def _register(client: TestClient, email: str) -> dict:
    res = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_team_owner(email: str) -> Organization:
    """Bypasses the Stripe webhook entirely -- team_service.ensure_organization
    is exactly what the webhook calls, so exercising it directly here keeps
    the invite/accept/remove tests focused on membership logic, not billing
    plumbing (that's covered by test_webhook_team_tier_creates_organization
    below)."""
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == email))
        user.tier = "team"
        session.add(user)
        session.commit()
        org = team_service.ensure_organization(session, user)
        return org


def test_webhook_team_tier_creates_organization(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(billing_module.config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(billing_module.config, "STRIPE_WEBHOOK_SECRET", None)
    monkeypatch.setattr(billing_module.config, "STRIPE_PRICE_ID_TEAM", "price_team_fake")

    with TestClient(app) as client:
        _register(client, "team-owner@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "team-owner@example.com"))
            user.stripe_customer_id = "cus_team_test"
            session.add(user)
            session.commit()

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_team_fake",
                    "customer": "cus_team_test",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_team_fake"}}]},
                }
            },
        }
        res = client.post("/billing/webhook", json=event)
        assert res.status_code == 200

        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == "team-owner@example.com"))
            assert user.tier == "team"
            org = session.scalar(select(Organization).where(Organization.owner_user_id == user.user_id))
            assert org is not None
            assert org.seat_count == 1
            assert user.organization_id == org.organization_id


def test_invite_requires_team_org(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "not-a-team-owner@example.com")
        res = client.post("/billing/team/invite", json={"email": "anyone@example.com"}, headers=headers)
        assert res.status_code == 404


def test_invite_requires_existing_account(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "owner1@example.com")
        _make_team_owner("owner1@example.com")

        res = client.post(
            "/billing/team/invite", json={"email": "never-signed-up@example.com"}, headers=headers
        )
        assert res.status_code == 404
        assert "register first" in res.json()["detail"]


def test_invite_and_accept_flow(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner2@example.com")
        _make_team_owner("owner2@example.com")
        member_headers = _register(client, "member2@example.com")

        captured = {}
        monkeypatch.setattr(
            billing_module,
            "send_email",
            lambda to, subject, body: captured.update(to=to, subject=subject, body=body),
        )

        invite_res = client.post(
            "/billing/team/invite", json={"email": "member2@example.com"}, headers=owner_headers
        )
        assert invite_res.status_code == 200
        assert captured["to"] == "member2@example.com"
        assert "invited" in captured["body"].lower()

        # Pull the raw token back out of the DB the way the test can (the
        # endpoint only emails it -- extract via the hash-lookup helper
        # by re-deriving from the DB is impossible since only the hash is
        # stored, so instead read the email body the invite embedded).
        assert "token=" in captured["body"]
        raw_token = captured["body"].split("token=")[1].split()[0].rstrip(".")

        accept_res = client.post(
            "/billing/team/accept", json={"token": raw_token}, headers=member_headers
        )
        assert accept_res.status_code == 200
        assert accept_res.json()["seat_count"] == 2

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member2@example.com"))
            owner = session.scalar(select(User).where(User.email == "owner2@example.com"))
            assert member.organization_id == owner.organization_id


def test_accept_rejects_wrong_user(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner3@example.com")
        org = _make_team_owner("owner3@example.com")
        _register(client, "invitee3@example.com")
        stranger_headers = _register(client, "stranger3@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            invitee = session.scalar(select(User).where(User.email == "invitee3@example.com"))
            invite, raw_token = team_service.invite_member(session, org, invitee.email)

        res = client.post("/billing/team/accept", json={"token": raw_token}, headers=stranger_headers)
        assert res.status_code == 403
        _ = owner_headers  # not needed beyond org creation


def test_accept_rejects_expired_invite(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        _register(client, "owner4@example.com")
        org = _make_team_owner("owner4@example.com")
        member_headers = _register(client, "member4@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member4@example.com"))
            invite, raw_token = team_service.invite_member(session, org, member.email)
            invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            session.add(invite)
            session.commit()

        res = client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)
        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()


def test_double_accept_rejected(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        _register(client, "owner5@example.com")
        org = _make_team_owner("owner5@example.com")
        member_headers = _register(client, "member5@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member5@example.com"))
            invite, raw_token = team_service.invite_member(session, org, member.email)

        first = client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)
        assert first.status_code == 200

        second = client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)
        assert second.status_code == 400


def test_invite_rejects_user_already_on_a_team(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner6@example.com")
        _make_team_owner("owner6@example.com")
        _register(client, "already-on-team6@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            already = session.scalar(select(User).where(User.email == "already-on-team6@example.com"))
            already.organization_id = 999999  # any non-null value is enough to trip the check
            session.add(already)
            session.commit()

        res = client.post(
            "/billing/team/invite", json={"email": "already-on-team6@example.com"}, headers=owner_headers
        )
        assert res.status_code == 409


def test_list_team_members_shows_owner_and_accepted_member(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner7@example.com")
        org = _make_team_owner("owner7@example.com")
        member_headers = _register(client, "member7@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member7@example.com"))
            invite, raw_token = team_service.invite_member(session, org, member.email)
        client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)

        # Both the owner's and the member's view of the roster should match.
        for headers in (owner_headers, member_headers):
            res = client.get("/billing/team/members", headers=headers)
            assert res.status_code == 200
            emails = {m["email"] for m in res.json()}
            assert emails == {"owner7@example.com", "member7@example.com"}
            owner_entry = next(m for m in res.json() if m["email"] == "owner7@example.com")
            assert owner_entry["is_owner"] is True


def test_list_team_members_404_for_non_member(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "solo8@example.com")
        res = client.get("/billing/team/members", headers=headers)
        assert res.status_code == 404


def test_remove_member_decrements_seat_count(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner9@example.com")
        org = _make_team_owner("owner9@example.com")
        member_headers = _register(client, "member9@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member9@example.com"))
            invite, raw_token = team_service.invite_member(session, org, member.email)
        client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)

        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member9@example.com"))
            assert member.organization_id is not None

        res = client.delete(f"/billing/team/members/{member.user_id}", headers=owner_headers)
        assert res.status_code == 200
        assert res.json()["seat_count"] == 1

        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member9@example.com"))
            assert member.organization_id is None


def test_remove_member_requires_owner(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        _register(client, "owner10@example.com")
        org = _make_team_owner("owner10@example.com")
        member_headers = _register(client, "member10@example.com")

        session_factory = get_session_factory()
        with session_factory() as session:
            member = session.scalar(select(User).where(User.email == "member10@example.com"))
            invite, raw_token = team_service.invite_member(session, org, member.email)
        client.post("/billing/team/accept", json={"token": raw_token}, headers=member_headers)

        with session_factory() as session:
            owner = session.scalar(select(User).where(User.email == "owner10@example.com"))

        # The member (not the owner) tries to remove the owner -- rejected
        # because member_headers' caller owns no org at all, not because of
        # a "can't remove owner" check specifically (that's the next test).
        res = client.delete(f"/billing/team/members/{owner.user_id}", headers=member_headers)
        assert res.status_code == 404


def test_owner_cannot_remove_self(seeded_sqlite_db, monkeypatch):
    monkeypatch.setattr(team_service, "sync_stripe_seats", lambda org: None)

    with TestClient(app) as client:
        owner_headers = _register(client, "owner11@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            owner = session.scalar(select(User).where(User.email == "owner11@example.com"))
        _make_team_owner("owner11@example.com")

        res = client.delete(f"/billing/team/members/{owner.user_id}", headers=owner_headers)
        assert res.status_code == 400

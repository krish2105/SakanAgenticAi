"""Phase 3 -- auth hardening: refresh tokens, logout, account lockout,
password reset, email verification, and RBAC.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

import app.routers.auth as auth_router
from app.auth import hash_password
from app.db import get_session_factory
from app.main import app
from app.models import User


def _register(client, email="user@example.com", password="correct-horse-1"):
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def test_register_and_login_return_refresh_tokens(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client)
        assert reg["access_token"] and reg["refresh_token"]

        login = client.post(
            "/auth/login", json={"email": "user@example.com", "password": "correct-horse-1"}
        )
        assert login.status_code == 200
        assert login.json()["refresh_token"]


def test_demo_login_creates_a_fresh_ephemeral_user_each_call(seeded_sqlite_db):
    with TestClient(app) as client:
        first = client.post("/auth/demo")
        assert first.status_code == 201, first.text
        assert first.json()["access_token"] and first.json()["refresh_token"]

        second = client.post("/auth/demo")
        assert second.status_code == 201

        # Two clicks -> two different, unrelated accounts -- confirms this
        # isn't one shared login whose quota everyone drains together.
        me1 = client.get("/auth/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"}).json()
        me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {second.json()['access_token']}"}).json()
        assert me1["user_id"] != me2["user_id"]
        assert me1["email"].startswith("demo+") and me1["email"].endswith("@sakan.internal")
        assert me1["email_verified"] is True


def test_demo_login_gets_a_real_starter_quota(seeded_sqlite_db):
    with TestClient(app) as client:
        demo = client.post("/auth/demo").json()
        billing = client.get(
            "/billing/me", headers={"Authorization": f"Bearer {demo['access_token']}"}
        ).json()
        assert billing["tier"] == "starter"
        assert billing["monthly_query_limit"] == 5


def test_refresh_rotates_and_old_token_is_revoked(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client)
        old_refresh = reg["refresh_token"]

        first = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert first.status_code == 200
        new_access = first.json()["access_token"]
        new_refresh = first.json()["refresh_token"]
        assert new_refresh and new_refresh != old_refresh

        # The rotated-out token can't be reused.
        reused = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert reused.status_code == 401

        # The new access token works.
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
        assert me.status_code == 200


def test_logout_revokes_refresh_token(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client)
        refresh = reg["refresh_token"]

        out = client.post("/auth/logout", json={"refresh_token": refresh})
        assert out.status_code == 204

        after = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert after.status_code == 401


def test_account_lockout_after_repeated_failures(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client, email="lock@example.com", password="correct-horse-1")
        for _ in range(5):
            bad = client.post(
                "/auth/login", json={"email": "lock@example.com", "password": "wrong-password"}
            )
            assert bad.status_code == 401

        # Even the correct password is now refused (locked, 429).
        locked = client.post(
            "/auth/login", json={"email": "lock@example.com", "password": "correct-horse-1"}
        )
        assert locked.status_code == 429


def test_email_verification_flow(seeded_sqlite_db, monkeypatch):
    captured = {}

    def fake_send(to, link):
        captured["link"] = link

    monkeypatch.setattr(auth_router, "send_verification_email", fake_send)

    with TestClient(app) as client:
        reg = _register(client, email="verify@example.com")
        token = parse_qs(urlparse(captured["link"]).query)["token"][0]

        # Before verifying.
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {reg['access_token']}"})
        assert me.json()["email_verified"] is False

        res = client.post("/auth/verify", json={"token": token})
        assert res.status_code == 200

        me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {reg['access_token']}"})
        assert me2.json()["email_verified"] is True

        # Token is single-use.
        assert client.post("/auth/verify", json={"token": token}).status_code == 400


def test_password_reset_flow(seeded_sqlite_db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        auth_router, "send_password_reset_email", lambda to, link: captured.__setitem__("link", link)
    )

    with TestClient(app) as client:
        _register(client, email="reset@example.com", password="original-pass-1")

        forgot = client.post("/auth/forgot", json={"email": "reset@example.com"})
        assert forgot.status_code == 202
        token = parse_qs(urlparse(captured["link"]).query)["token"][0]

        res = client.post("/auth/reset", json={"token": token, "new_password": "brand-new-pass-2"})
        assert res.status_code == 200

        # Old password no longer works; new one does.
        old = client.post(
            "/auth/login", json={"email": "reset@example.com", "password": "original-pass-1"}
        )
        assert old.status_code == 401
        new = client.post(
            "/auth/login", json={"email": "reset@example.com", "password": "brand-new-pass-2"}
        )
        assert new.status_code == 200


def test_forgot_password_does_not_leak_account_existence(seeded_sqlite_db):
    with TestClient(app) as client:
        # Unknown email still returns 202, no signal that it doesn't exist.
        res = client.post("/auth/forgot", json={"email": "nobody@example.com"})
        assert res.status_code == 202


def test_self_registration_cannot_create_admin(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post(
            "/auth/register",
            json={"email": "wannabe-admin@example.com", "password": "correct-horse-1", "role": "Admin"},
        )
        assert res.status_code == 422


def test_rbac_admin_stats_requires_admin_role(seeded_sqlite_db):
    with TestClient(app) as client:
        # A normal Agent is forbidden.
        reg = _register(client, email="agent@example.com")
        forbidden = client.get("/admin/stats", headers={"Authorization": f"Bearer {reg['access_token']}"})
        assert forbidden.status_code == 403

        # Promote a user to Admin directly in the DB, then log in.
        session_factory = get_session_factory()
        with session_factory() as session:
            admin = User(
                email="admin@example.com",
                hashed_password=hash_password("correct-horse-1"),
                role="Admin",
            )
            session.add(admin)
            session.commit()

        login = client.post(
            "/auth/login", json={"email": "admin@example.com", "password": "correct-horse-1"}
        )
        token = login.json()["access_token"]
        ok = client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200
        assert "total_users" in ok.json()

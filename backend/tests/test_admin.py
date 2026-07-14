"""Phase 10b -- admin dashboard backend surface: user list/search, tier
override, query volume. /admin/stats itself is already covered by
test_auth_hardening.py's RBAC test; this file covers the newer endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import hash_password
from app.db import get_session_factory
from app.main import app
from app.models import User


def _register(client, email="user@example.com", password="correct-horse-1"):
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def _make_admin_token(client, seeded_sqlite_db) -> str:
    # /auth/register's lazy create_all is what actually creates the users
    # table in a fresh SQLite test DB (Alembic owns it in production) --
    # inserting a User row directly first would 500 with "no such table"
    # unless a registration has already happened via the API at least once.
    _register(client, email="_table-bootstrap@example.com")

    session_factory = get_session_factory()
    with session_factory() as session:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("correct-horse-1"),
            role="Admin",
        )
        session.add(admin)
        session.commit()
    login = client.post("/auth/login", json={"email": "admin@example.com", "password": "correct-horse-1"})
    return login.json()["access_token"]


def test_admin_users_requires_admin_role(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client, email="agent@example.com")
        res = client.get("/admin/users", headers={"Authorization": f"Bearer {reg['access_token']}"})
        assert res.status_code == 403


def test_admin_users_lists_and_searches(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client, email="alice@example.com")
        _register(client, email="bob@example.com")
        token = _make_admin_token(client, seeded_sqlite_db)
        headers = {"Authorization": f"Bearer {token}"}

        all_users = client.get("/admin/users", headers=headers).json()
        # alice, bob, the admin account, plus _make_admin_token's own
        # table-bootstrap registration.
        assert all_users["total"] == 4
        emails = {u["email"] for u in all_users["users"]}
        assert {"alice@example.com", "bob@example.com", "admin@example.com"} <= emails

        filtered = client.get("/admin/users", params={"q": "alice"}, headers=headers).json()
        assert filtered["total"] == 1
        assert filtered["users"][0]["email"] == "alice@example.com"


def test_admin_users_pagination_clamps_limit(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client, email="agent@example.com")
        token = _make_admin_token(client, seeded_sqlite_db)
        res = client.get("/admin/users", params={"limit": 500}, headers={"Authorization": f"Bearer {token}"})
        assert res.json()["limit"] == 100


def test_admin_tier_override_updates_user(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client, email="agent@example.com")
        token = _make_admin_token(client, seeded_sqlite_db)
        headers = {"Authorization": f"Bearer {token}"}

        user_id = client.get("/admin/users", params={"q": "agent"}, headers=headers).json()["users"][0][
            "user_id"
        ]
        res = client.patch(f"/admin/users/{user_id}/tier", json={"tier": "pro"}, headers=headers)
        assert res.status_code == 200
        assert res.json() == {"user_id": user_id, "tier": "pro"}

        # Reflected back in the list.
        listed = client.get("/admin/users", params={"q": "agent"}, headers=headers).json()["users"][0]
        assert listed["tier"] == "pro"


def test_admin_tier_override_rejects_unknown_tier(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client, email="agent@example.com")
        token = _make_admin_token(client, seeded_sqlite_db)
        headers = {"Authorization": f"Bearer {token}"}
        user_id = client.get("/admin/users", params={"q": "agent"}, headers=headers).json()["users"][0][
            "user_id"
        ]
        res = client.patch(f"/admin/users/{user_id}/tier", json={"tier": "diamond"}, headers=headers)
        assert res.status_code == 400


def test_admin_tier_override_404_for_unknown_user(seeded_sqlite_db):
    with TestClient(app) as client:
        token = _make_admin_token(client, seeded_sqlite_db)
        res = client.patch(
            "/admin/users/999999/tier",
            json={"tier": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


def test_admin_tier_override_requires_admin_role(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client, email="agent@example.com")
        session_factory = get_session_factory()
        with session_factory() as session:
            user_id = session.scalars(select(User.user_id).where(User.email == "agent@example.com")).one()
        res = client.patch(
            f"/admin/users/{user_id}/tier",
            json={"tier": "pro"},
            headers={"Authorization": f"Bearer {reg['access_token']}"},
        )
        assert res.status_code == 403


def test_admin_query_volume_requires_admin_role(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client, email="agent@example.com")
        res = client.get("/admin/query-volume", headers={"Authorization": f"Bearer {reg['access_token']}"})
        assert res.status_code == 403


def test_admin_query_volume_returns_list(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client, email="agent@example.com")
        client.post(
            "/deals/query",
            json={"raw_query": "2BR Dubai Marina"},
            headers={"Authorization": f"Bearer {reg['access_token']}"},
        )
        token = _make_admin_token(client, seeded_sqlite_db)
        res = client.get("/admin/query-volume", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert sum(day["count"] for day in body) >= 1

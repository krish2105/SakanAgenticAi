"""Phase 16 -- free security/trust layer: Cloudflare Turnstile bot
verification on register/login, and the active-sessions UI (list, revoke
one, log out everywhere) built on the existing refresh-token infrastructure.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.routers.auth as auth_router
from app.main import app
from app.services import turnstile as turnstile_module


def _register(client, email="user@example.com", password="correct-horse-1"):
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


# --- Turnstile: unit tests against the service module directly -------------


@pytest.mark.anyio
async def test_turnstile_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(turnstile_module.config, "TURNSTILE_SECRET_KEY", None)
    assert await turnstile_module.verify_turnstile_token(None) is True
    assert await turnstile_module.verify_turnstile_token("anything") is True


@pytest.mark.anyio
async def test_turnstile_rejects_missing_token_when_configured(monkeypatch):
    monkeypatch.setattr(turnstile_module.config, "TURNSTILE_SECRET_KEY", "fake-secret")
    assert await turnstile_module.verify_turnstile_token(None) is False
    assert await turnstile_module.verify_turnstile_token("") is False


@pytest.mark.anyio
async def test_turnstile_respects_siteverify_success_field(monkeypatch):
    monkeypatch.setattr(turnstile_module.config, "TURNSTILE_SECRET_KEY", "fake-secret")

    class FakeResponse:
        def __init__(self, success):
            self._success = success

        def raise_for_status(self):
            pass

        def json(self):
            return {"success": self._success}

    class FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, data):
            return FakeResponse(data.get("__force_success", True))

    monkeypatch.setattr(turnstile_module.httpx, "AsyncClient", FakeAsyncClient)
    assert await turnstile_module.verify_turnstile_token("good-token") is True


@pytest.mark.anyio
async def test_turnstile_fails_open_on_network_error(monkeypatch):
    monkeypatch.setattr(turnstile_module.config, "TURNSTILE_SECRET_KEY", "fake-secret")

    class BrokenAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, data):
            raise ConnectionError("simulated Cloudflare outage")

    monkeypatch.setattr(turnstile_module.httpx, "AsyncClient", BrokenAsyncClient)
    # Infra failure -> fail open, so a Cloudflare outage can't lock out every
    # signup/login. Distinct from an explicit {"success": false} rejection.
    assert await turnstile_module.verify_turnstile_token("some-token") is True


# --- Turnstile wired into register/login (integration) ---------------------


def test_register_rejects_when_turnstile_configured_and_verification_fails(seeded_sqlite_db, monkeypatch):
    async def _fail(*a, **k):
        return False

    monkeypatch.setattr(auth_router, "verify_turnstile_token", _fail)
    with TestClient(app) as client:
        res = client.post("/auth/register", json={"email": "bot@example.com", "password": "correct-horse-1"})
        assert res.status_code == 400
        assert "bot verification" in res.json()["detail"].lower()


def test_login_rejects_when_turnstile_configured_and_verification_fails(seeded_sqlite_db, monkeypatch):
    with TestClient(app) as client:
        _register(client, email="human@example.com")

        async def _fail(*a, **k):
            return False

        monkeypatch.setattr(auth_router, "verify_turnstile_token", _fail)
        res = client.post("/auth/login", json={"email": "human@example.com", "password": "correct-horse-1"})
        assert res.status_code == 400


# --- Active sessions: list / revoke one / revoke all ------------------------


def test_list_sessions_shows_metadata_for_the_session_just_created(seeded_sqlite_db):
    with TestClient(app) as client:
        # The User-Agent on the *registering* request is what gets recorded on
        # the session -- it's captured when the refresh token is issued, not
        # when the session list is later read back.
        res = client.post(
            "/auth/register",
            json={"email": "user@example.com", "password": "correct-horse-1"},
            headers={"User-Agent": "pytest-agent/1.0"},
        )
        assert res.status_code == 201
        access = res.json()["access_token"]

        sessions = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access}"}).json()
        assert len(sessions) == 1
        assert sessions[0]["user_agent"] == "pytest-agent/1.0"
        assert sessions[0]["id"] is not None
        assert sessions[0]["created_at"]


def test_delete_session_revokes_it_and_its_refresh_token_stops_working(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client)
        access, refresh = reg["access_token"], reg["refresh_token"]

        sessions = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access}"}).json()
        session_id = sessions[0]["id"]

        deleted = client.delete(f"/auth/sessions/{session_id}", headers={"Authorization": f"Bearer {access}"})
        assert deleted.status_code == 204

        refreshed = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert refreshed.status_code == 401


def test_delete_session_is_scoped_to_the_owning_user(seeded_sqlite_db):
    with TestClient(app) as client:
        reg_a = _register(client, email="a@example.com")
        reg_b = _register(client, email="b@example.com")

        sessions_a = client.get(
            "/auth/sessions", headers={"Authorization": f"Bearer {reg_a['access_token']}"}
        ).json()
        session_id_a = sessions_a[0]["id"]

        # b tries to delete a's session id -- not found, not someone else's data.
        res = client.delete(
            f"/auth/sessions/{session_id_a}", headers={"Authorization": f"Bearer {reg_b['access_token']}"}
        )
        assert res.status_code == 404

        # a's session is still intact.
        still_there = client.get(
            "/auth/sessions", headers={"Authorization": f"Bearer {reg_a['access_token']}"}
        ).json()
        assert len(still_there) == 1


def test_revoke_all_sessions_logs_out_every_refresh_token(seeded_sqlite_db):
    with TestClient(app) as client:
        reg = _register(client)
        access = reg["access_token"]
        refresh_1 = reg["refresh_token"]

        # A second "device" logging in creates a second active session.
        login = client.post("/auth/login", json={"email": "user@example.com", "password": "correct-horse-1"})
        refresh_2 = login.json()["refresh_token"]

        sessions = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access}"}).json()
        assert len(sessions) == 2

        out = client.post("/auth/sessions/revoke-all", headers={"Authorization": f"Bearer {access}"})
        assert out.status_code == 204

        assert client.post("/auth/refresh", json={"refresh_token": refresh_1}).status_code == 401
        assert client.post("/auth/refresh", json={"refresh_token": refresh_2}).status_code == 401


def test_sessions_endpoints_require_auth(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/auth/sessions").status_code in (401, 403)
        assert client.delete("/auth/sessions/1").status_code in (401, 403)
        assert client.post("/auth/sessions/revoke-all").status_code in (401, 403)

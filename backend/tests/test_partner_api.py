"""Phase 20 -- partner/embed API: key issuance, ownership-scoped revocation,
and the rate-limited X-API-Key-authenticated comps endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _register(client, email="partner@example.com", password="correct-horse-1"):
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def test_create_and_list_api_key(seeded_sqlite_db):
    with TestClient(app) as client:
        access = _register(client)

        created = client.post(
            "/partner/api-keys", json={"name": "My integration"}, headers={"Authorization": f"Bearer {access}"}
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["api_key"].startswith("sk_live_")
        assert body["key_prefix"] in body["api_key"]

        listed = client.get("/partner/api-keys", headers={"Authorization": f"Bearer {access}"}).json()
        assert len(listed) == 1
        assert listed[0]["name"] == "My integration"
        # The raw key is never returned again after creation.
        assert "api_key" not in listed[0]


def test_delete_api_key_is_scoped_to_the_owning_user(seeded_sqlite_db):
    with TestClient(app) as client:
        access_a = _register(client, email="a@example.com")
        access_b = _register(client, email="b@example.com")

        created = client.post(
            "/partner/api-keys", json={"name": "A's key"}, headers={"Authorization": f"Bearer {access_a}"}
        ).json()

        # b tries to delete a's key id -- not found, not someone else's data.
        res = client.delete(f"/partner/api-keys/{created['id']}", headers={"Authorization": f"Bearer {access_b}"})
        assert res.status_code == 404

        still_there = client.get("/partner/api-keys", headers={"Authorization": f"Bearer {access_a}"}).json()
        assert len(still_there) == 1

        deleted = client.delete(f"/partner/api-keys/{created['id']}", headers={"Authorization": f"Bearer {access_a}"})
        assert deleted.status_code == 204
        gone = client.get("/partner/api-keys", headers={"Authorization": f"Bearer {access_a}"}).json()
        assert len(gone) == 0


def test_partner_comps_requires_api_key(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/partner/v1/comps")
        assert res.status_code == 401
        assert "X-API-Key" in res.json()["detail"]


def test_partner_comps_rejects_invalid_key(seeded_sqlite_db):
    with TestClient(app) as client:
        _register(client)  # triggers /auth/register's lazy create_all() -- api_keys included
        res = client.get("/partner/v1/comps", headers={"X-API-Key": "sk_live_not-a-real-key"})
        assert res.status_code == 401


def test_partner_comps_returns_data_for_a_valid_key(seeded_sqlite_db):
    with TestClient(app) as client:
        access = _register(client)
        created = client.post(
            "/partner/api-keys", json={"name": "Integration"}, headers={"Authorization": f"Bearer {access}"}
        ).json()

        res = client.get(
            "/partner/v1/comps", params={"limit": 5}, headers={"X-API-Key": created["api_key"]}
        )
        assert res.status_code == 200
        comps = res.json()
        assert isinstance(comps, list)
        assert len(comps) <= 5


def test_usage_endpoint_requires_auth(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/partner/usage").status_code == 401


def test_usage_tracks_authenticated_calls_and_ignores_invalid_ones(seeded_sqlite_db):
    with TestClient(app) as client:
        access = _register(client)
        created = client.post(
            "/partner/api-keys", json={"name": "Integration"}, headers={"Authorization": f"Bearer {access}"}
        ).json()

        empty = client.get("/partner/usage", headers={"Authorization": f"Bearer {access}"})
        assert empty.status_code == 200
        assert empty.json() == {"days": []}

        for _ in range(3):
            res = client.get("/partner/v1/comps", headers={"X-API-Key": created["api_key"]})
            assert res.status_code == 200

        # An invalid key must not inflate the count.
        client.get("/partner/v1/comps", headers={"X-API-Key": "sk_live_not-a-real-key"})

        usage = client.get("/partner/usage", headers={"Authorization": f"Bearer {access}"}).json()
        assert len(usage["days"]) == 1  # all calls land on today
        assert usage["days"][0]["count"] == 3


def test_usage_is_scoped_to_the_owning_user(seeded_sqlite_db):
    with TestClient(app) as client:
        access_a = _register(client, email="usage-a@example.com")
        access_b = _register(client, email="usage-b@example.com")

        key_a = client.post(
            "/partner/api-keys", json={"name": "A's key"}, headers={"Authorization": f"Bearer {access_a}"}
        ).json()

        client.get("/partner/v1/comps", headers={"X-API-Key": key_a["api_key"]})

        usage_b = client.get("/partner/usage", headers={"Authorization": f"Bearer {access_b}"}).json()
        assert usage_b == {"days": []}


def test_partner_comps_rejects_a_revoked_key(seeded_sqlite_db):
    with TestClient(app) as client:
        access = _register(client)
        created = client.post(
            "/partner/api-keys", json={"name": "Integration"}, headers={"Authorization": f"Bearer {access}"}
        ).json()

        client.delete(f"/partner/api-keys/{created['id']}", headers={"Authorization": f"Bearer {access}"})

        res = client.get("/partner/v1/comps", headers={"X-API-Key": created["api_key"]})
        assert res.status_code == 401

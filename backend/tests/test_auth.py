from fastapi.testclient import TestClient

from app.main import app


def test_register_then_login(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post(
            "/auth/register",
            json={"email": "new-agent@example.com", "password": "correct-horse-1", "full_name": "Test Agent"},
        )
        assert res.status_code == 201
        assert res.json()["token_type"] == "bearer"
        assert res.json()["access_token"]

        res = client.post("/auth/login", json={"email": "new-agent@example.com", "password": "correct-horse-1"})
        assert res.status_code == 200
        token = res.json()["access_token"]

        res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == "new-agent@example.com"
        assert body["full_name"] == "Test Agent"
        assert body["role"] == "Agent"


def test_register_rejects_duplicate_email(seeded_sqlite_db):
    with TestClient(app) as client:
        first = client.post("/auth/register", json={"email": "dupe@example.com", "password": "correct-horse-1"})
        assert first.status_code == 201

        second = client.post("/auth/register", json={"email": "dupe@example.com", "password": "another-password"})
        assert second.status_code == 409


def test_register_rejects_short_password(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post("/auth/register", json={"email": "weak@example.com", "password": "short"})
        assert res.status_code == 422


def test_login_rejects_wrong_password(seeded_sqlite_db):
    with TestClient(app) as client:
        client.post("/auth/register", json={"email": "wrongpw@example.com", "password": "correct-horse-1"})
        res = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "not-the-password"})
        assert res.status_code == 401


def test_login_rejects_unknown_email(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-1"})
        assert res.status_code == 401


def test_me_requires_a_token(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert res.status_code == 401


def test_email_is_case_insensitive_on_login(seeded_sqlite_db):
    with TestClient(app) as client:
        client.post("/auth/register", json={"email": "MixedCase@Example.com", "password": "correct-horse-1"})
        res = client.post("/auth/login", json={"email": "mixedcase@example.com", "password": "correct-horse-1"})
        assert res.status_code == 200

"""Phase 25 -- saved-search email digests: CRUD, ownership scoping, and the
run_all_digests entry point scripts/send_search_digests.py calls on a cron.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import app.services.alerts_service as alerts_service
from app.db import get_session_factory
from app.main import app
from app.models import SavedSearch


def _register(client: TestClient, email: str) -> dict:
    res = client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_create_list_and_delete_saved_search(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "alerts-crud@example.com")

        created = client.post(
            "/alerts",
            json={"community": "Dubai Marina", "property_type": "Apartment", "bedrooms": 2},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["community"] == "Dubai Marina"
        assert body["last_notified_at"] is None

        listed = client.get("/alerts", headers=headers).json()
        assert len(listed) == 1
        assert listed[0]["id"] == body["id"]

        deleted = client.delete(f"/alerts/{body['id']}", headers=headers)
        assert deleted.status_code == 204
        assert client.get("/alerts", headers=headers).json() == []


def test_saved_search_is_ownership_scoped(seeded_sqlite_db):
    with TestClient(app) as client:
        headers_a = _register(client, "alerts-a@example.com")
        headers_b = _register(client, "alerts-b@example.com")

        created = client.post("/alerts", json={"community": "Downtown Dubai"}, headers=headers_a).json()

        # b can't see or delete a's saved search.
        assert client.get("/alerts", headers=headers_b).json() == []
        assert client.delete(f"/alerts/{created['id']}", headers=headers_b).status_code == 404

        still_there = client.get("/alerts", headers=headers_a).json()
        assert len(still_there) == 1


def test_alerts_require_auth(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/alerts").status_code == 401
        assert client.post("/alerts", json={}).status_code == 401


def test_run_all_digests_sends_only_for_searches_with_matches(seeded_sqlite_db, monkeypatch):
    sent_emails = []
    monkeypatch.setattr(alerts_service, "send_email", lambda to, subject, body: sent_emails.append((to, subject, body)))

    with TestClient(app) as client:
        headers = _register(client, "digest-recipient@example.com")

        # A search that matches real seeded data.
        client.post("/alerts", json={"community": "Dubai Marina"}, headers=headers)
        # A search for a community that doesn't exist in the seeded dataset.
        client.post("/alerts", json={"community": "Nonexistent Community XYZ"}, headers=headers)

    session_factory = get_session_factory()
    with session_factory() as session:
        sent = alerts_service.run_all_digests(session)

    assert sent == 1
    assert len(sent_emails) == 1
    to, subject, body = sent_emails[0]
    assert to == "digest-recipient@example.com"
    assert "saved search digest" in subject
    assert "Dubai Marina" in body


def test_run_all_digests_respects_the_minimum_resend_interval(seeded_sqlite_db, monkeypatch):
    sent_emails = []
    monkeypatch.setattr(alerts_service, "send_email", lambda to, subject, body: sent_emails.append(to))

    with TestClient(app) as client:
        headers = _register(client, "digest-throttle@example.com")
        client.post("/alerts", json={"community": "Dubai Marina"}, headers=headers)

    session_factory = get_session_factory()
    with session_factory() as session:
        first_run = alerts_service.run_all_digests(session)
        second_run = alerts_service.run_all_digests(session)

    assert first_run == 1
    assert second_run == 0  # too soon since last_notified_at
    assert len(sent_emails) == 1


def test_run_all_digests_skips_a_search_whose_owner_no_longer_exists(seeded_sqlite_db, monkeypatch):
    sent_emails = []
    monkeypatch.setattr(alerts_service, "send_email", lambda to, subject, body: sent_emails.append(to))

    with TestClient(app) as client:
        # Triggers ensure_users_table()'s lazy create_all -- this test writes
        # directly via the session factory afterward, without going through
        # any endpoint that would otherwise create the tables as a side effect.
        _register(client, "table-bootstrap@example.com")

    session_factory = get_session_factory()
    with session_factory() as session:
        orphan = SavedSearch(owner_id=999999, community="Dubai Marina")
        session.add(orphan)
        session.commit()

        sent = alerts_service.run_all_digests(session)

    assert sent == 0
    assert sent_emails == []

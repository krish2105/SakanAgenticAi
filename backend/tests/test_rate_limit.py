from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session_factory
from app.main import app
from app.models import User
from app.routers.deals import limiter


def test_deal_query_is_rate_limited_per_client(seeded_sqlite_db):
    """POST /deals/query is the endpoint that spends Anthropic budget per call,
    so it carries its own rate limit independent of any account-level quota.
    Confirms the limiter actually rejects requests, not just that it's wired.

    slowapi's default storage is in-memory and keyed by client IP; every
    TestClient shares the same fixed pseudo-IP, so the limiter's counters
    persist across tests in the same pytest process unless explicitly reset.
    """
    limiter.reset()
    try:
        with TestClient(app) as client:
            res = client.post("/auth/register", json={"email": "ratelimit@example.com", "password": "correct-horse-1"})
            headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

            # This test exercises the per-request rate limit (12 requests/minute
            # cap), which is a different mechanism than the monthly billing
            # quota (test_billing.py). Bump to an unmetered tier so the two
            # don't interfere with each other.
            session_factory = get_session_factory()
            with session_factory() as session:
                user = session.scalar(select(User).where(User.email == "ratelimit@example.com"))
                user.tier = "team"
                session.add(user)
                session.commit()

            statuses = [
                client.post("/deals/query", json={"raw_query": f"query {i}"}, headers=headers).status_code
                for i in range(12)
            ]

            assert statuses[:10] == [202] * 10
            assert 429 in statuses[10:]
    finally:
        limiter.reset()  # don't leak this test's consumed quota into whatever runs next

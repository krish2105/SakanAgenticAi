import time

from fastapi.testclient import TestClient

import app.agents.compliance_agent as compliance_agent_module
import app.agents.query_agent as query_agent_module
from app.main import app

SAMPLE_CLAUSES = [
    {
        "clause_id": "ESCROW-1",
        "text": "No developer may collect any payment from a buyer outside of a project-specific escrow account.",
        "source_doc": "escrow_account_regulations.md",
        "doc_category": "escrow",
        "similarity": 0.91,
    },
]


def _fake_query_json(system_prompt, user_content, model, max_tokens=1024):
    return {
        "query_type": "full_memo",
        "community": "Dubai Marina",
        "property_type": "Apartment",
        "bedrooms": 2,
        "budget_min": 1800000,
        "budget_max": 2200000,
        "project_id": None,
    }


def _fake_compliance_json(system_prompt, user_content, model, max_tokens=1024):
    return {
        "compliance_flags": [],
        "compliance_summary": "No issues found per ESCROW-1.",
        "cited_clause_ids": ["ESCROW-1"],
    }


def _register(client: TestClient, email: str, password: str = "correct-horse-1") -> dict:
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_comps_endpoint_filters_seeded_data(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/comps", params={"community": "Dubai Marina", "type": "Apartment", "bedrooms": 2})
        assert res.status_code == 200
        comps = res.json()
        assert isinstance(comps, list)
        for c in comps:
            assert c["community"] == "Dubai Marina"
            assert c["property_type"] == "Apartment"
            assert c["bedrooms"] == 2


def test_market_ticker_and_trends(seeded_sqlite_db):
    with TestClient(app) as client:
        ticker = client.get("/market/ticker", params={"limit": 5}).json()
        assert len(ticker) <= 5
        assert all({"building", "community", "beds", "price", "type"} <= set(t.keys()) for t in ticker)

        summary = client.get("/market/trends", params={"view": "summary"}).json()
        assert len(summary) > 0
        assert "avg_price_per_sqft" in summary[0]

        developers = client.get("/market/trends", params={"view": "developers"}).json()
        assert len(developers) == 15

        off_plan = client.get("/market/trends", params={"view": "off_plan"}).json()
        assert len(off_plan) == 20


def test_deal_query_full_lifecycle(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        headers = _register(client, "lifecycle@example.com")

        res = client.post("/deals/query", json={"raw_query": "full memo for a 2BR in Dubai Marina"}, headers=headers)
        assert res.status_code == 202
        query_id = res.json()["query_id"]
        assert query_id.isdigit()

        deal = None
        for _ in range(50):
            deal = client.get(f"/deals/{query_id}", headers=headers).json()
            if deal.get("memo_markdown"):
                break
            time.sleep(0.1)

        assert deal is not None
        assert deal["query_type"] == "full_memo"
        assert deal["memo_markdown"]
        assert deal["compliance_summary"] == "No issues found per ESCROW-1."

        trace = client.get(f"/deals/{query_id}/trace", headers=headers).json()
        done_agents = [t["agent"] for t in trace["agent_trace"] if t["status"] == "done"]
        assert done_agents == ["query", "comps", "valuation", "compliance", "memo"]

        memo = client.get(f"/deals/{query_id}/memo", headers=headers).json()
        assert memo["memo_markdown"] == deal["memo_markdown"]

        pdf_res = client.get(f"/deals/{query_id}/memo", params={"format": "pdf"}, headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content[:4] == b"%PDF"

        # A different user must not be able to read this deal (guessable-ID leak closed).
        other_headers = _register(client, "someone-else@example.com")
        assert client.get(f"/deals/{query_id}", headers=other_headers).status_code == 404


def test_deal_query_rejects_empty_query(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "empty-query@example.com")
        res = client.post("/deals/query", json={"raw_query": "   "}, headers=headers)
        assert res.status_code == 422


def test_deal_query_requires_auth(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post("/deals/query", json={"raw_query": "2BR Dubai Marina"})
        assert res.status_code == 401


def test_get_unknown_deal_is_404(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "unknown-deal@example.com")
        res = client.get("/deals/999999", headers=headers)
        assert res.status_code == 404


def test_get_deal_without_auth_is_401(seeded_sqlite_db):
    with TestClient(app) as client:
        assert client.get("/deals/1").status_code == 401


def test_ws_stream_receives_state_and_complete(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        res = client.post("/auth/register", json={"email": "ws-user@example.com", "password": "correct-horse-1"})
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post("/deals/query", json={"raw_query": "full memo for JVC 1BR"}, headers=headers)
        query_id = res.json()["query_id"]

        with client.websocket_connect(f"/ws/deals/{query_id}/stream?token={token}") as ws:
            messages = []
            for _ in range(20):
                msg = ws.receive_json()
                messages.append(msg)
                if msg["type"] in ("complete", "error"):
                    break

        assert messages[-1]["type"] == "complete"
        assert messages[-1]["data"]["memo_markdown"]


def test_ws_stream_without_token_is_rejected(seeded_sqlite_db):
    with TestClient(app) as client:
        headers = _register(client, "ws-no-token@example.com")
        res = client.post("/deals/query", json={"raw_query": "2BR JVC"}, headers=headers)
        query_id = res.json()["query_id"]

        from starlette.websockets import WebSocketDisconnect

        try:
            with client.websocket_connect(f"/ws/deals/{query_id}/stream") as ws:
                ws.receive_json()
            assert False, "expected the connection to be rejected"
        except WebSocketDisconnect as exc:
            assert exc.code == 4401

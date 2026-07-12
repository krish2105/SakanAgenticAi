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
        res = client.post("/deals/query", json={"raw_query": "full memo for a 2BR in Dubai Marina"})
        assert res.status_code == 202
        query_id = res.json()["query_id"]
        assert query_id.isdigit()

        deal = None
        for _ in range(50):
            deal = client.get(f"/deals/{query_id}").json()
            if deal.get("memo_markdown"):
                break
            time.sleep(0.1)

        assert deal is not None
        assert deal["query_type"] == "full_memo"
        assert deal["memo_markdown"]
        assert deal["compliance_summary"] == "No issues found per ESCROW-1."

        trace = client.get(f"/deals/{query_id}/trace").json()
        done_agents = [t["agent"] for t in trace["agent_trace"] if t["status"] == "done"]
        assert done_agents == ["query", "comps", "valuation", "compliance", "memo"]

        memo = client.get(f"/deals/{query_id}/memo").json()
        assert memo["memo_markdown"] == deal["memo_markdown"]

        pdf_res = client.get(f"/deals/{query_id}/memo", params={"format": "pdf"})
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content[:4] == b"%PDF"


def test_deal_query_rejects_empty_query(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.post("/deals/query", json={"raw_query": "   "})
        assert res.status_code == 422


def test_get_unknown_deal_is_404(seeded_sqlite_db):
    with TestClient(app) as client:
        res = client.get("/deals/999999")
        assert res.status_code == 404


def test_ws_stream_receives_state_and_complete(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        res = client.post("/deals/query", json={"raw_query": "full memo for JVC 1BR"})
        query_id = res.json()["query_id"]

        with client.websocket_connect(f"/ws/deals/{query_id}/stream") as ws:
            messages = []
            for _ in range(20):
                msg = ws.receive_json()
                messages.append(msg)
                if msg["type"] in ("complete", "error"):
                    break

        assert messages[-1]["type"] == "complete"
        assert messages[-1]["data"]["memo_markdown"]

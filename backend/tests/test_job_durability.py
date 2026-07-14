"""Phase 4 -- job durability: a persisted, authoritative status column on
DealQuery (pending -> running -> done|failed) and the retry endpoint it
enables. Also covers Phase 7-free: data_provenance surfaced on comps.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

import app.agents.compliance_agent as compliance_agent_module
import app.agents.query_agent as query_agent_module
import app.services.pipeline_runner as pipeline_runner_module
from app.agents.graph import get_deal_pipeline as _real_get_deal_pipeline
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


def _wait_for(client, query_id, headers, predicate, attempts=50):
    deal = None
    for _ in range(attempts):
        deal = client.get(f"/deals/{query_id}", headers=headers).json()
        if predicate(deal):
            return deal
        time.sleep(0.1)
    return deal


def test_successful_run_persists_done_status_and_attempt_count(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        headers = _register(client, "durability-success@example.com")
        res = client.post("/deals/query", json={"raw_query": "full memo for a 2BR in Dubai Marina"}, headers=headers)
        query_id = res.json()["query_id"]

        deal = _wait_for(client, query_id, headers, lambda d: d.get("job_status") in ("done", "failed"))
        assert deal["job_status"] == "done"
        assert deal["attempt_count"] == 1


def test_failed_run_persists_failed_status_and_is_retryable(monkeypatch, seeded_sqlite_db):
    # Force a genuine top-level pipeline failure (not one an individual agent's
    # own try/except would swallow) by breaking pipeline construction itself.
    def _raise(*a, **k):
        raise RuntimeError("simulated pipeline construction failure")

    monkeypatch.setattr(pipeline_runner_module, "get_deal_pipeline", _raise)

    with TestClient(app) as client:
        headers = _register(client, "durability-fail@example.com")
        res = client.post("/deals/query", json={"raw_query": "anything"}, headers=headers)
        assert res.status_code == 202
        query_id = res.json()["query_id"]

        deal = _wait_for(client, query_id, headers, lambda d: d.get("job_status") in ("done", "failed"))
        assert deal["job_status"] == "failed"
        assert deal["attempt_count"] == 1
        assert any(
            t.get("agent") == "pipeline" and "simulated pipeline construction failure" in (t.get("detail") or "")
            for t in deal["agent_trace"]
        )

        # Fix the pipeline, then retry: should transition away from "failed".
        # Restore explicitly (not monkeypatch.undo()) -- undo() would also revert
        # the seeded_sqlite_db fixture's DATABASE_URL override, since it shares
        # this same monkeypatch instance, breaking the DB connection entirely.
        monkeypatch.setattr(pipeline_runner_module, "get_deal_pipeline", _real_get_deal_pipeline)
        monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
        monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
        monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

        retry_res = client.post(f"/deals/{query_id}/retry", headers=headers)
        assert retry_res.status_code == 202
        assert retry_res.json()["query_id"] == query_id

        deal2 = _wait_for(client, query_id, headers, lambda d: d.get("job_status") == "done")
        assert deal2["job_status"] == "done"
        assert deal2["attempt_count"] == 2  # first failed attempt + this retry


def test_retry_rejected_when_not_failed(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        headers = _register(client, "durability-notfailed@example.com")
        res = client.post("/deals/query", json={"raw_query": "full memo"}, headers=headers)
        query_id = res.json()["query_id"]
        _wait_for(client, query_id, headers, lambda d: d.get("job_status") == "done")

        retry_res = client.post(f"/deals/{query_id}/retry", headers=headers)
        assert retry_res.status_code == 409


def test_retry_requires_ownership(monkeypatch, seeded_sqlite_db):
    def _raise(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_runner_module, "get_deal_pipeline", _raise)

    with TestClient(app) as client:
        owner_headers = _register(client, "durability-owner@example.com")
        other_headers = _register(client, "durability-other@example.com")

        res = client.post("/deals/query", json={"raw_query": "anything"}, headers=owner_headers)
        query_id = res.json()["query_id"]
        _wait_for(client, query_id, owner_headers, lambda d: d.get("job_status") == "failed")

        # A different user can't retry someone else's deal (and can't tell it exists).
        assert client.post(f"/deals/{query_id}/retry", headers=other_headers).status_code == 404
        assert client.post("/deals/999999/retry", headers=owner_headers).status_code == 404


def test_retry_does_not_consume_additional_quota(monkeypatch, seeded_sqlite_db):
    def _raise(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_runner_module, "get_deal_pipeline", _raise)

    with TestClient(app) as client:
        headers = _register(client, "durability-quota@example.com")
        res = client.post("/deals/query", json={"raw_query": "anything"}, headers=headers)
        query_id = res.json()["query_id"]
        _wait_for(client, query_id, headers, lambda d: d.get("job_status") == "failed")

        before = client.get("/billing/me", headers=headers).json()["queries_used_this_month"]
        client.post(f"/deals/{query_id}/retry", headers=headers)
        _wait_for(client, query_id, headers, lambda d: d.get("attempt_count", 0) >= 2)
        after = client.get("/billing/me", headers=headers).json()["queries_used_this_month"]

        assert after == before  # quota counts rows created, not run attempts


def test_comps_endpoint_surfaces_data_provenance(seeded_sqlite_db):
    with TestClient(app) as client:
        comps = client.get("/comps", params={"limit": 5}).json()
        assert len(comps) > 0
        assert all(c["data_provenance"] == "synthetic" for c in comps)


def test_deal_pipeline_comps_include_data_provenance(monkeypatch, seeded_sqlite_db):
    monkeypatch.setattr(query_agent_module, "complete_json", _fake_query_json)
    monkeypatch.setattr(compliance_agent_module, "retrieve_clauses", lambda q, **k: SAMPLE_CLAUSES)
    monkeypatch.setattr(compliance_agent_module, "complete_json", _fake_compliance_json)

    with TestClient(app) as client:
        headers = _register(client, "provenance-pipeline@example.com")
        res = client.post("/deals/query", json={"raw_query": "full memo for a 2BR in Dubai Marina"}, headers=headers)
        query_id = res.json()["query_id"]
        deal = _wait_for(client, query_id, headers, lambda d: d.get("job_status") == "done")

        assert deal["retrieved_comps"]
        assert all(c.get("data_provenance") == "synthetic" for c in deal["retrieved_comps"])

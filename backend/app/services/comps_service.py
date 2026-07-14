"""Structured SQL comp retrieval + semantic re-rank (ARCHITECTURE.md Section 5.3)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ENABLE_SEMANTIC_EMBEDDINGS
from app.models import Building, Transaction

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

_embedder_load_failed = False


def _get_embedder():
    """Returns the shared sentence-transformers singleton (same instance the
    Compliance Agent's retrieval.py uses -- see ingest_regulations.get_embedder,
    cached via lru_cache). Two independently-cached copies of the same ~90MB
    model plus its torch backend were enough to OOM a 512MB free-tier
    container the moment a single pipeline run touched both this agent and
    the Compliance Agent (comps_search-only queries never hit that path,
    which is why this went unnoticed until query_agent's routing fix let
    valuation/compliance/full_memo queries actually reach both). Even a
    single instance turned out to be enough on its own -- see
    ENABLE_SEMANTIC_EMBEDDINGS in app/config.py -- so this is off by
    default; returns None (rather than raising) whenever it can't or
    shouldn't load, so semantic_rerank degrades to a heuristic instead of
    crashing the pipeline."""
    global _embedder_load_failed
    if not ENABLE_SEMANTIC_EMBEDDINGS or _embedder_load_failed:
        return None
    try:
        from ingest_regulations import get_embedder

        return get_embedder()
    except Exception:  # noqa: BLE001
        _embedder_load_failed = True
        return None


def query_transactions_sql(
    session: Session,
    community: str | None,
    property_type: str | None,
    bedrooms: int | None,
    budget_range: tuple[float | None, float | None],
    limit: int = 25,
) -> list[dict]:
    budget_min, budget_max = budget_range
    stmt = select(Transaction, Building.name.label("building_name")).join(
        Building, Transaction.building_id == Building.building_id, isouter=True
    )

    if community:
        stmt = stmt.where(Transaction.community == community)
    if property_type:
        stmt = stmt.where(Transaction.property_type == property_type)
    if bedrooms is not None:
        stmt = stmt.where(Transaction.bedrooms == bedrooms)
    if budget_min is not None:
        stmt = stmt.where(Transaction.price_aed >= budget_min * 0.85)
    if budget_max is not None:
        stmt = stmt.where(Transaction.price_aed <= budget_max * 1.15)

    stmt = stmt.order_by(Transaction.transaction_date.desc()).limit(limit)

    rows = session.execute(stmt).all()
    comps = []
    for txn, building_name in rows:
        comps.append(
            {
                "transaction_id": txn.transaction_id,
                "building": building_name or txn.building_id,
                "community": txn.community,
                "property_type": txn.property_type,
                "bedrooms": txn.bedrooms,
                "size_sqft": float(txn.size_sqft) if txn.size_sqft is not None else None,
                "price": float(txn.price_aed) if txn.price_aed is not None else None,
                "price_per_sqft": float(txn.price_per_sqft) if txn.price_per_sqft is not None else None,
                "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
                # Phase 7: surfaced end-to-end (API -> UI) so a user can always
                # tell whether a comp is synthetic demo data, the real DLD/Kaggle
                # open dataset, or (once one exists) a licensed partner feed --
                # see app/services/data_source.py and README "Data partnership".
                "data_provenance": txn.data_provenance,
            }
        )
    return comps


def _comp_description(comp: dict) -> str:
    return (
        f"{comp.get('bedrooms')}BR {comp.get('property_type')} in {comp.get('building')}, "
        f"{comp.get('community')}, {comp.get('size_sqft')} sqft, AED {comp.get('price')}"
    )


def _recency_score(comp: dict) -> float:
    if not comp.get("date"):
        return 0.0
    try:
        d = date.fromisoformat(comp["date"])
    except ValueError:
        return 0.0
    days_old = (date.today() - d).days
    return max(0.0, 1.0 - days_old / 548)


def semantic_rerank(comps: list[dict], query: str, top_k: int = 8) -> list[dict]:
    """Re-ranks structured SQL comps against the free-text query.

    Uses cosine similarity between sentence-transformer embeddings when the
    model is available; otherwise falls back to a recency-weighted heuristic
    so the pipeline still returns a sensible top_k without network access.
    """
    if not comps:
        return []

    embedder = _get_embedder()
    if embedder is not None:

        texts = [query] + [_comp_description(c) for c in comps]
        vectors = embedder.encode(texts, normalize_embeddings=True)
        query_vec, comp_vecs = vectors[0], vectors[1:]
        scores = comp_vecs @ query_vec
        ranked = sorted(zip(comps, scores), key=lambda cs: cs[1], reverse=True)
    else:
        ranked = sorted(comps, key=_recency_score, reverse=True)
        ranked = [(c, _recency_score(c)) for c in ranked]

    return [c for c, _ in ranked[:top_k]]

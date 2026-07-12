"""Structured SQL comp retrieval + semantic re-rank (ARCHITECTURE.md Section 5.3)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Building, Transaction

_embedder = None
_embedder_load_failed = False


def _get_embedder():
    """Lazily loads the sentence-transformers model. Returns None (rather
    than raising) if it can't be loaded -- e.g. no network access to
    Hugging Face -- so semantic_rerank degrades to a heuristic instead of
    crashing the pipeline."""
    global _embedder, _embedder_load_failed
    if _embedder is not None or _embedder_load_failed:
        return _embedder
    try:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:  # noqa: BLE001
        _embedder_load_failed = True
        _embedder = None
    return _embedder


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
        import numpy as np

        texts = [query] + [_comp_description(c) for c in comps]
        vectors = embedder.encode(texts, normalize_embeddings=True)
        query_vec, comp_vecs = vectors[0], vectors[1:]
        scores = comp_vecs @ query_vec
        ranked = sorted(zip(comps, scores), key=lambda cs: cs[1], reverse=True)
    else:
        ranked = sorted(comps, key=_recency_score, reverse=True)
        ranked = [(c, _recency_score(c)) for c in ranked]

    return [c for c, _ in ranked[:top_k]]

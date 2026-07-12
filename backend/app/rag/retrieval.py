"""Retrieval over the sakan_regulations Qdrant collection for the
Compliance RAG Agent (ARCHITECTURE.md Section 5.5)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from ingest_regulations import COLLECTION_NAME, build_qdrant_client, get_embedder  # noqa: E402
from app.config import QDRANT_URL  # noqa: E402


def compose_retrieval_query(
    property_type: str | None, community: str | None, is_off_plan: bool, raw_query: str
) -> str:
    return (
        f"{property_type or 'property'} in {community or 'Dubai'}, off-plan: {is_off_plan}, "
        f"RERA Form requirements, escrow, foreign ownership. Context: {raw_query}"
    )


def retrieve_clauses(
    query_text: str,
    top_k: int = 6,
    client=None,
    embedder=None,
) -> list[dict]:
    """Returns [{clause_id, text, source_doc, similarity}], per DealState.retrieved_clauses."""
    client = client or build_qdrant_client(QDRANT_URL)
    embedder = embedder or get_embedder()

    vector = embedder.encode([query_text], normalize_embeddings=True)[0]
    results = client.query_points(
        collection_name=COLLECTION_NAME, query=vector.tolist(), limit=top_k
    ).points

    return [
        {
            "clause_id": r.payload["clause_id"],
            "text": r.payload["text"],
            "source_doc": r.payload["source_doc"],
            "doc_category": r.payload.get("doc_category"),
            "similarity": round(float(r.score), 4),
        }
        for r in results
    ]

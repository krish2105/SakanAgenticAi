"""Retrieval over the sakan_regulations Qdrant collection for the
Compliance RAG Agent (ARCHITECTURE.md Section 5.5)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from ingest_regulations import COLLECTION_NAME, build_qdrant_client  # noqa: E402
from app.config import ENABLE_SEMANTIC_EMBEDDINGS, QDRANT_API_KEY, QDRANT_URL  # noqa: E402
from app.embeddings import get_embedder  # noqa: E402


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
    """Returns [{clause_id, text, source_doc, doc_category, similarity,
    review_status, reviewed_by, review_date}], per DealState.retrieved_clauses.

    The review_* fields (Phase D: "a named legal/compliance partner") ride
    along from the corpus's own frontmatter (see ingest_regulations.py) so
    a retrieved clause can honestly say whether counsel has actually
    looked at it, per-clause, rather than one blanket disclaimer covering
    a corpus that's entirely unreviewed today.
    """
    if not ENABLE_SEMANTIC_EMBEDDINGS and embedder is None:
        raise RuntimeError(
            "Semantic search is disabled on this deployment (no embeddings provider "
            "configured), so compliance falls back to an honest 'unable to verify' "
            "instead of guessing. Set GEMINI_API_KEY (free tier, see app/embeddings.py) "
            "or ENABLE_SEMANTIC_EMBEDDINGS=true to enable it."
        )

    client = client or build_qdrant_client(QDRANT_URL, api_key=QDRANT_API_KEY)
    embedder = embedder or get_embedder()
    collection_name = getattr(embedder, "collection_name", COLLECTION_NAME)

    vector = embedder.encode([query_text], normalize_embeddings=True, task_type="RETRIEVAL_QUERY")[0]
    results = client.query_points(
        collection_name=collection_name, query=vector.tolist(), limit=top_k
    ).points

    return [
        {
            "clause_id": r.payload["clause_id"],
            "text": r.payload["text"],
            "source_doc": r.payload["source_doc"],
            "doc_category": r.payload.get("doc_category"),
            "similarity": round(float(r.score), 4),
            "review_status": r.payload.get("review_status", "unreviewed"),
            "reviewed_by": r.payload.get("reviewed_by"),
            "review_date": r.payload.get("review_date"),
        }
        for r in results
    ]

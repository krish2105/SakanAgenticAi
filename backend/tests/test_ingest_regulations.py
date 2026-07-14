import hashlib
from pathlib import Path

import numpy as np

from scripts.ingest_regulations import (
    EMBEDDING_DIM,
    COLLECTION_NAME,
    build_qdrant_client,
    load_all_chunks,
    parse_doc,
    upsert_chunks,
)

REGULATIONS_DIR = Path(__file__).resolve().parents[2] / "regulations"


class FakeEmbedder:
    """Deterministic, network-free stand-in for SentenceTransformer in tests.

    Real embeddings require downloading sentence-transformers/all-MiniLM-L6-v2
    from Hugging Face, which this sandbox has no network access to. This
    fake preserves the property that matters for retrieval correctness --
    identical text yields identical vectors, different text yields
    different vectors -- via a seeded hash, so the Qdrant round-trip and
    query-similarity logic are still exercised end-to-end.
    """

    def encode(self, texts, show_progress_bar=False, normalize_embeddings=True, task_type="RETRIEVAL_DOCUMENT"):
        del task_type  # deterministic fake ignores it, same as the real local embedder
        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            v = rng.normal(size=EMBEDDING_DIM)
            if normalize_embeddings:
                v = v / np.linalg.norm(v)
            vectors.append(v)
        return np.array(vectors)


def test_parse_doc_extracts_frontmatter_and_clauses():
    chunks = parse_doc(REGULATIONS_DIR / "rera_form_f_sale_purchase_agreement.md")
    assert len(chunks) >= 4
    assert all(c.doc_id == "RERA-F" for c in chunks)
    assert all(c.doc_category == "sale_purchase_agreement" for c in chunks)
    assert all(c.applies_to == ["off_plan"] for c in chunks)
    ids = [c.clause_id for c in chunks]
    assert "RERA-F-1" in ids
    assert all(50 <= len(c.text.split()) <= 400 for c in chunks)
    # Legal-review attribution (Phase D) -- every doc in this repo is
    # honestly unreviewed today; see LEGAL_REVIEW.md.
    assert all(c.review_status == "unreviewed" for c in chunks)
    assert all(c.reviewed_by is None for c in chunks)


def test_parse_doc_rejects_reviewed_status_without_reviewer():
    import pytest
    import tempfile

    bad_doc = """---
doc_id: TEST
title: Test Doc
doc_category: test
applies_to: [both]
review_status: reviewed
---

## TEST-1: A clause

Some clause text that is long enough to pass the word-count style checks in this fixture file for testing purposes here.
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(bad_doc)
        path = Path(f.name)
    try:
        with pytest.raises(ValueError, match="reviewed_by"):
            parse_doc(path)
    finally:
        path.unlink()


def test_all_twelve_regulatory_docs_present_and_parseable():
    md_files = sorted(REGULATIONS_DIR.glob("*.md"))
    assert len(md_files) == 12

    chunks = load_all_chunks(REGULATIONS_DIR)
    assert len(chunks) >= 12 * 4  # at least 4 clauses per doc on average

    doc_ids = {c.doc_id for c in chunks}
    expected_doc_ids = {
        "RERA-A", "RERA-B", "RERA-F", "ESCROW", "OFFPLAN", "OQOOD",
        "TITLE", "AIDISC", "FOREIGN", "RDC", "SERVICE", "MORTGAGE",
    }
    assert doc_ids == expected_doc_ids

    # Every clause_id within a doc must be unique (citation integrity).
    for doc_id in doc_ids:
        clause_ids = [c.clause_id for c in chunks if c.doc_id == doc_id]
        assert len(clause_ids) == len(set(clause_ids))


def test_upsert_and_query_round_trip_with_in_memory_qdrant():
    chunks = load_all_chunks(REGULATIONS_DIR)
    client = build_qdrant_client(":memory:")
    embedder = FakeEmbedder()

    n = upsert_chunks(chunks, client, embedder=embedder)
    assert n == len(chunks)
    assert client.count(COLLECTION_NAME).count == len(chunks)

    query_text = next(c.text for c in chunks if c.clause_id == "ESCROW-1")
    query_vector = embedder.encode([query_text])[0].tolist()
    results = client.query_points(collection_name=COLLECTION_NAME, query=query_vector, limit=3).points

    assert len(results) == 3
    assert results[0].payload["clause_id"] == "ESCROW-1"
    for r in results:
        assert set(r.payload.keys()) >= {"doc_id", "clause_id", "doc_category", "applies_to", "source_doc", "text"}
        assert r.payload["review_status"] == "unreviewed"

#!/usr/bin/env python3
"""
Chunks the synthetic regulatory corpus in regulations/ and upserts it into a
Qdrant `sakan_regulations` collection, per ARCHITECTURE.md Section 6.

Each doc carries YAML frontmatter (doc_id, title, doc_category, applies_to)
and is split into clauses on `## <CLAUSE-ID>: <Title>` headings — each
clause becomes one chunk (roughly 300-500 tokens, matching the spec), with
metadata {doc_id, clause_id, doc_category, applies_to} attached so the
Compliance RAG Agent can cite retrieved clauses precisely.

Usage:
    python ingest_regulations.py --regulations-dir regulations --qdrant-url http://localhost:6333
    python ingest_regulations.py --dry-run   # parse + chunk only, no embedding/Qdrant needed
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COLLECTION_NAME = "sakan_regulations"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
CLAUSE_RE = re.compile(r"^##\s+([A-Z0-9\-]+):\s*(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    doc_id: str
    clause_id: str
    title: str
    doc_category: str
    applies_to: list[str]
    source_doc: str
    text: str
    # Legal-review attribution (Phase D: "a named legal/compliance partner").
    # Every doc in this repo is synthetic and unreviewed -- these fields
    # exist so a real engagement has somewhere to record itself per-clause
    # (not just one blanket disclaimer), not because a review has happened.
    # See LEGAL_REVIEW.md for what that engagement looks like.
    review_status: str = "unreviewed"  # unreviewed | pending_review | reviewed
    reviewed_by: str | None = None
    review_date: str | None = None


def parse_doc(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"{path} is missing YAML frontmatter")

    frontmatter = yaml.safe_load(match.group(1))
    body = match.group(2).strip()

    doc_id = frontmatter["doc_id"]
    doc_category = frontmatter["doc_category"]
    applies_to = frontmatter.get("applies_to", ["both"])
    review_status = frontmatter.get("review_status", "unreviewed")
    reviewed_by = frontmatter.get("reviewed_by")
    review_date = frontmatter.get("review_date")
    if review_status not in ("unreviewed", "pending_review", "reviewed"):
        raise ValueError(f"{path} has an invalid review_status: {review_status!r}")
    if review_status == "reviewed" and not reviewed_by:
        raise ValueError(f"{path} is marked reviewed but has no reviewed_by -- who reviewed it?")

    headings = list(CLAUSE_RE.finditer(body))
    if not headings:
        raise ValueError(f"{path} has no '## CLAUSE-ID: Title' sections")

    chunks: list[Chunk] = []
    for i, m in enumerate(headings):
        clause_id, title = m.group(1), m.group(2).strip()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        text = body[start:end].strip()
        chunks.append(
            Chunk(
                doc_id=doc_id,
                clause_id=clause_id,
                title=title,
                doc_category=doc_category,
                applies_to=applies_to,
                source_doc=path.name,
                text=text,
                review_status=review_status,
                reviewed_by=reviewed_by,
                review_date=review_date,
            )
        )
    return chunks


def load_all_chunks(regulations_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(regulations_dir.glob("*.md")):
        chunks.extend(parse_doc(path))
    return chunks


def get_embedder(model_name: str = EMBEDDING_MODEL):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def build_qdrant_client(qdrant_url: str, api_key: str | None = None):
    from qdrant_client import QdrantClient

    if qdrant_url == ":memory:":
        return QdrantClient(location=":memory:")
    return QdrantClient(url=qdrant_url, api_key=api_key)


def upsert_chunks(chunks: list[Chunk], client, embedder=None) -> int:
    from qdrant_client.http import models as qmodels

    embedder = embedder or get_embedder()
    vectors = embedder.encode([c.text for c in chunks], show_progress_bar=False, normalize_embeddings=True)

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=EMBEDDING_DIM, distance=qmodels.Distance.COSINE),
        )

    points = [
        qmodels.PointStruct(
            id=i,
            vector=vectors[i].tolist(),
            payload={**asdict(chunks[i])},
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regulations-dir", type=Path, default=Path("regulations"))
    parser.add_argument("--qdrant-url", type=str, default=os.environ.get("QDRANT_URL", "http://localhost:6333"))
    parser.add_argument(
        "--qdrant-api-key",
        type=str,
        default=os.environ.get("QDRANT_API_KEY"),
        help="Required for Qdrant Cloud; unused for self-hosted Qdrant. Defaults to $QDRANT_API_KEY.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk only; skip embedding + Qdrant")
    args = parser.parse_args()

    chunks = load_all_chunks(args.regulations_dir)
    print(f"Parsed {len(chunks)} clauses from {len(list(args.regulations_dir.glob('*.md')))} documents.")

    for c in chunks[:3]:
        print(f"  [{c.doc_id}] {c.clause_id}: {c.title} ({len(c.text.split())} words)")

    if args.dry_run:
        print("Dry run — skipping embedding/Qdrant upsert.")
        return

    client = build_qdrant_client(args.qdrant_url, api_key=args.qdrant_api_key)
    n = upsert_chunks(chunks, client)
    print(f"Upserted {n} clauses into Qdrant collection '{COLLECTION_NAME}' at {args.qdrant_url}.")


if __name__ == "__main__":
    main()

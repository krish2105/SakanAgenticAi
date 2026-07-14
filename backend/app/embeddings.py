"""Embedding provider dispatch for semantic RAG.

Mirrors app/llm.py's provider-dispatch pattern. Two backends:

- GeminiEmbedder: calls Google's free `gemini-embedding-001` API. The model
  runs on Google's infrastructure, not this process, so it costs zero local
  RAM -- the thing that forced ENABLE_SEMANTIC_EMBEDDINGS off by default on a
  512MB free-tier host in the first place. Free tier (mid-2026): 10M
  tokens/minute, no daily request cap. Wins whenever GEMINI_API_KEY is set.
- LocalEmbedder: the original sentence-transformers/all-MiniLM-L6-v2 model,
  resident in-process. Still available for a host with RAM to spare and no
  Google account -- opt in with ENABLE_SEMANTIC_EMBEDDINGS=true.

The two backends produce differently-sized vectors, so they cannot share a
Qdrant collection -- each embedder carries its own `collection_name` so
ingest_regulations.py and rag/retrieval.py write to and read from the right
one without either module needing to know which provider is active.
"""
from __future__ import annotations

import functools

import numpy as np

from app import config

LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LOCAL_EMBEDDING_DIM = 384
LOCAL_COLLECTION_NAME = "sakan_regulations"

GEMINI_MODEL_NAME = "gemini-embedding-001"
# Gemini's native output is 3072-dim; truncated to 768 here -- plenty of
# separation for a 12-document regulatory corpus, at a quarter of the
# storage/bandwidth of the full vector.
GEMINI_EMBEDDING_DIM = 768
GEMINI_COLLECTION_NAME = "sakan_regulations_gemini"


class LocalEmbedder:
    """In-process sentence-transformers model. RAM-heavy (~200-400MB
    resident with its torch backend) -- see ENABLE_SEMANTIC_EMBEDDINGS in
    app/config.py for why this is opt-in, not default."""

    dim = LOCAL_EMBEDDING_DIM
    collection_name = LOCAL_COLLECTION_NAME

    def __init__(self, model_name: str = LOCAL_MODEL_NAME):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> np.ndarray:
        del task_type  # local model has no asymmetric query/doc mode
        return self._model.encode(
            texts, show_progress_bar=show_progress_bar, normalize_embeddings=normalize_embeddings
        )


class GeminiEmbedder:
    """Calls gemini-embedding-001 over the network. No local model weights,
    so this works on any free-tier host regardless of RAM. Uses Gemini's
    task_type parameter to get its asymmetric retrieval quality boost -- a
    short query and the longer document it should match are embedded
    slightly differently on purpose (RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT),
    per Google's embedding API docs."""

    dim = GEMINI_EMBEDDING_DIM
    collection_name = GEMINI_COLLECTION_NAME

    def __init__(self, api_key: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key or config.GEMINI_API_KEY)

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> np.ndarray:
        del show_progress_bar  # no local progress to report for a remote API call
        from google.genai import types

        result = self._client.models.embed_content(
            model=GEMINI_MODEL_NAME,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dim),
        )
        vectors = np.array([e.values for e in result.embeddings], dtype=np.float64)
        if normalize_embeddings:
            # Only Gemini's native 3072-dim output is pre-normalized to unit
            # length; a truncated output_dimensionality must be renormalized
            # by hand (per Google's embedding API docs).
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.clip(norms, 1e-12, None)
        return vectors


@functools.lru_cache(maxsize=1)
def get_embedder():
    """Gemini wins whenever GEMINI_API_KEY is set -- it costs no local RAM,
    so there's no reason to prefer the local model once a free key exists.
    Falls back to the local model only when ENABLE_SEMANTIC_EMBEDDINGS is
    explicitly turned on without a Gemini key (a host with RAM to spare and
    no Google account). Raises when neither is available; callers (comps
    reranking, compliance retrieval) already have documented fallback
    behavior for this case."""
    if config.GEMINI_API_KEY:
        return GeminiEmbedder()
    if config.ENABLE_SEMANTIC_EMBEDDINGS:
        return LocalEmbedder()
    raise RuntimeError(
        "No embedding provider available -- set GEMINI_API_KEY (free, no local RAM cost) "
        "or ENABLE_SEMANTIC_EMBEDDINGS=true on a host with enough RAM for the local model."
    )

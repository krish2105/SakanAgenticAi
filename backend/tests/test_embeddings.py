import numpy as np
import pytest

from app import embeddings


@pytest.fixture(autouse=True)
def _clear_embedder_cache():
    embeddings.get_embedder.cache_clear()
    yield
    embeddings.get_embedder.cache_clear()


def test_get_embedder_prefers_gemini_when_key_set(monkeypatch):
    monkeypatch.setattr(embeddings.config, "GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(embeddings.config, "ENABLE_SEMANTIC_EMBEDDINGS", True)
    sentinel = object()
    monkeypatch.setattr(embeddings, "GeminiEmbedder", lambda: sentinel)
    assert embeddings.get_embedder() is sentinel


def test_get_embedder_falls_back_to_local_without_gemini_key(monkeypatch):
    monkeypatch.setattr(embeddings.config, "GEMINI_API_KEY", None)
    monkeypatch.setattr(embeddings.config, "ENABLE_SEMANTIC_EMBEDDINGS", True)
    sentinel = object()
    monkeypatch.setattr(embeddings, "LocalEmbedder", lambda: sentinel)
    assert embeddings.get_embedder() is sentinel


def test_get_embedder_raises_when_neither_available(monkeypatch):
    monkeypatch.setattr(embeddings.config, "GEMINI_API_KEY", None)
    monkeypatch.setattr(embeddings.config, "ENABLE_SEMANTIC_EMBEDDINGS", False)
    with pytest.raises(RuntimeError, match="No embedding provider"):
        embeddings.get_embedder()


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeResponse:
    def __init__(self, vectors):
        self.embeddings = [_FakeEmbedding(v) for v in vectors]


def test_gemini_embedder_renormalizes_truncated_vectors():
    """Only Gemini's native 3072-dim output is pre-normalized; a truncated
    output_dimensionality (this module uses 768) must be renormalized by
    hand, or downstream cosine-similarity search would be silently wrong."""
    embedder = embeddings.GeminiEmbedder.__new__(embeddings.GeminiEmbedder)

    class FakeModels:
        def embed_content(self, model, contents, config):
            rng = np.random.default_rng(0)
            # Scaled up to make sure normalization is actually doing work,
            # not passing through already-unit vectors by coincidence.
            vectors = [rng.normal(size=embeddings.GEMINI_EMBEDDING_DIM) * 5 for _ in contents]
            return _FakeResponse(vectors)

    class FakeClient:
        models = FakeModels()

    embedder._client = FakeClient()

    vectors = embedder.encode(["clause text one", "clause text two"], normalize_embeddings=True)
    norms = np.linalg.norm(vectors, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)


def test_gemini_embedder_passes_task_type_and_dim_through():
    embedder = embeddings.GeminiEmbedder.__new__(embeddings.GeminiEmbedder)
    seen = {}

    class FakeModels:
        def embed_content(self, model, contents, config):
            seen["task_type"] = config.task_type
            seen["output_dimensionality"] = config.output_dimensionality
            seen["model"] = model
            return _FakeResponse([[0.1] * embeddings.GEMINI_EMBEDDING_DIM for _ in contents])

    class FakeClient:
        models = FakeModels()

    embedder._client = FakeClient()
    embedder.encode(["a query"], task_type="RETRIEVAL_QUERY")

    assert seen["task_type"] == "RETRIEVAL_QUERY"
    assert seen["output_dimensionality"] == embeddings.GEMINI_EMBEDDING_DIM
    assert seen["model"] == embeddings.GEMINI_MODEL_NAME


def test_gemini_embedder_skips_renormalization_when_disabled():
    embedder = embeddings.GeminiEmbedder.__new__(embeddings.GeminiEmbedder)
    raw = [5.0] * embeddings.GEMINI_EMBEDDING_DIM

    class FakeModels:
        def embed_content(self, model, contents, config):
            return _FakeResponse([raw for _ in contents])

    class FakeClient:
        models = FakeModels()

    embedder._client = FakeClient()
    vectors = embedder.encode(["text"], normalize_embeddings=False)
    np.testing.assert_allclose(vectors[0], raw)


def test_local_and_gemini_embedders_have_distinct_collections_and_dims():
    # This is the reason upsert_chunks/retrieve_clauses key their Qdrant
    # collection off the active embedder rather than a fixed constant --
    # the two providers' vectors are not interchangeable.
    assert embeddings.LocalEmbedder.collection_name != embeddings.GeminiEmbedder.collection_name
    assert embeddings.LocalEmbedder.dim != embeddings.GeminiEmbedder.dim

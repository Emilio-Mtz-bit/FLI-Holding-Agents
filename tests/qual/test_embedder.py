import tempfile
import pytest
from agents.qual.models import Chunk
from agents.qual.embedder import EmbedderBase, SentenceTransformerEmbedder, ChromaStore


class FakeEmbedder(EmbedderBase):
    """Returns fixed-length zero vectors — avoids loading a real model in tests."""
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


def test_fake_embedder_returns_vectors_for_each_text():
    emb = FakeEmbedder()
    result = emb.embed(["hola", "mundo"])
    assert len(result) == 2
    assert len(result[0]) == 384


def test_chroma_store_stores_chunks_and_returns_count():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = ChromaStore(
            persist_path=tmpdir,
            collection_name="test",
            embedder=FakeEmbedder(),
        )
        chunks = [
            Chunk(text="chunk uno", source_path="a.txt", chunk_index=0),
            Chunk(text="chunk dos", source_path="a.txt", chunk_index=1),
        ]
        count = store.store(chunks)
        assert count == 2
        store.close()


def test_chroma_store_is_idempotent_on_same_collection():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = ChromaStore(
            persist_path=tmpdir,
            collection_name="test",
            embedder=FakeEmbedder(),
        )
        chunks = [Chunk(text="hola", source_path="b.txt", chunk_index=0)]
        store.store(chunks)
        store.close()
        # Second call should not raise
        store2 = ChromaStore(tmpdir, "test", FakeEmbedder())
        count = store2.store([Chunk(text="mundo", source_path="b.txt", chunk_index=1)])
        assert count == 1
        store2.close()

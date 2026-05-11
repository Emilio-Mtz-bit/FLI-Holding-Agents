from abc import ABC, abstractmethod
import chromadb
from agents.qual.models import Chunk


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder(EmbedderBase):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()


class ChromaStore:
    def __init__(self, persist_path: str, collection_name: str, embedder: EmbedderBase):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = embedder

    def store(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)
        ids = [f"{c.source_path}::chunk-{c.chunk_index}" for c in chunks]
        self.collection.add(documents=texts, embeddings=embeddings, ids=ids)
        return len(chunks)

    def close(self) -> None:
        """Release file handles held by the ChromaDB client (important on Windows)."""
        try:
            self.client.clear_system_cache()
        except Exception:
            pass

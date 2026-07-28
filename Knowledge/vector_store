"""
Vector store for semantic retrieval over regulatory chunks.

This is an in-memory implementation so the system runs with zero
external infrastructure. The interface (add / search) matches what
you'd get from Chroma/Weaviate/pgvector, so swapping the backing
store later doesn't require touching calling code.
"""

from dataclasses import dataclass

from knowledge.ingestion.chunker import Chunk
from knowledge.ingestion.embedder import cosine_similarity, embed_text
from core.config import settings


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


class VectorStore:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks.append(chunk)
            self._vectors.append(embed_text(chunk.text))

    def search(
        self,
        query: str,
        jurisdiction: str | None = None,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        query_vec = embed_text(query)
        top_k = top_k or settings.top_k_chunks
        min_similarity = min_similarity if min_similarity is not None else settings.min_similarity

        results = []
        for chunk, vec in zip(self._chunks, self._vectors):
            if jurisdiction and chunk.jurisdiction != jurisdiction:
                continue
            score = cosine_similarity(query_vec, vec)
            if score >= min_similarity:
                results.append(RetrievedChunk(chunk=chunk, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def all_jurisdictions(self) -> set[str]:
        return {c.jurisdiction for c in self._chunks}

    def size(self) -> int:
        return len(self._chunks)

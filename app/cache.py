"""Layer 1 — Semantic Cache.

Before spending a single token on generation, check whether we've already
answered something close enough to this question. Unlike Model Studio's
implicit *prefix* cache (which needs byte-identical prompt beginnings), this
matches on *meaning* via embedding similarity, so "what are your hours" and
"when are you open" collapse to one cached answer.

The cache is split into three swappable pieces so it can be tested offline:

- an ``EmbeddingProvider`` (see ``app.embeddings``) turns text into a vector,
- a ``VectorStore`` persists (query, response, embedding) and finds the nearest
  neighbour — ``InMemoryVectorStore`` for local/test, ``PgVectorStore`` for prod,
- ``SemanticCache`` ties them together and applies the similarity threshold.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Protocol, Tuple, runtime_checkable

from app import config
from app.embeddings import EmbeddingProvider
from app.vectormath import cosine_similarity


@dataclass
class CacheHit:
    response: str
    similarity: float
    original_query: str


@dataclass
class StoredEntry:
    query: str
    response: str
    embedding: List[float]


@runtime_checkable
class VectorStore(Protocol):
    def add(self, query: str, response: str, embedding: List[float]) -> None:
        ...

    def nearest(self, embedding: List[float]) -> Optional[Tuple[StoredEntry, float]]:
        """Return (entry, similarity) for the closest stored row, or None if empty."""
        ...


class InMemoryVectorStore:
    """A list-backed store with brute-force cosine search.

    Perfect for tests, local demos, and small corpora. Swap in
    ``PgVectorStore`` once the corpus is large enough to need an ANN index.
    """

    def __init__(self) -> None:
        self._entries: List[StoredEntry] = []

    def add(self, query: str, response: str, embedding: List[float]) -> None:
        self._entries.append(StoredEntry(query=query, response=response, embedding=list(embedding)))

    def nearest(self, embedding: List[float]) -> Optional[Tuple[StoredEntry, float]]:
        if not self._entries:
            return None
        best_entry = None
        best_sim = float("-inf")
        for entry in self._entries:
            sim = cosine_similarity(embedding, entry.embedding)
            if sim > best_sim:
                best_sim, best_entry = sim, entry
        assert best_entry is not None
        return best_entry, best_sim

    def __len__(self) -> int:
        return len(self._entries)


class PgVectorStore:
    """Postgres + pgvector store (production). Lazily uses an injected psycopg2
    connection; nothing here is imported during the test suite."""

    def __init__(self, conn, table: str = "tokentrim_cache"):
        self._conn = conn
        self._table = table

    def add(self, query: str, response: str, embedding: List[float]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._table} (query, response, embedding, created_at)
                VALUES (%s, %s, %s::vector, %s)
                """,
                (query, response, embedding, time.time()),
            )
        self._conn.commit()

    def nearest(self, embedding: List[float]) -> Optional[Tuple[StoredEntry, float]]:
        # pgvector cosine distance: 0 = identical, 2 = opposite. similarity = 1 - distance.
        from psycopg2.extras import RealDictCursor  # lazy

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT query, response, 1 - (embedding <=> %s::vector) AS similarity
                FROM {self._table}
                ORDER BY embedding <=> %s::vector
                LIMIT 1
                """,
                (embedding, embedding),
            )
            row = cur.fetchone()
        if row is None:
            return None
        entry = StoredEntry(query=row["query"], response=row["response"], embedding=[])
        return entry, float(row["similarity"])


class SemanticCache:
    def __init__(
        self,
        store: VectorStore,
        embedder: EmbeddingProvider,
        similarity_threshold: float = config.CACHE_SIMILARITY_THRESHOLD,
    ):
        self.store = store
        self.embedder = embedder
        self.threshold = similarity_threshold

    def lookup(self, query: str) -> Optional[CacheHit]:
        vec = self.embedder.embed(query)
        result = self.store.nearest(vec)
        if result is None:
            return None
        entry, similarity = result
        if similarity >= self.threshold:
            return CacheHit(
                response=entry.response,
                similarity=similarity,
                original_query=entry.query,
            )
        return None

    def store_answer(self, query: str, response: str) -> None:
        vec = self.embedder.embed(query)
        self.store.add(query, response, vec)

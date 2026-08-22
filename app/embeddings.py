"""Embedding providers for the semantic cache (Layer 1).

Two implementations behind one tiny interface:

- ``QwenEmbeddingProvider`` — the production path. Calls Alibaba's
  ``text-embedding-v4`` through the OpenAI-compatible client. Imports ``openai``
  lazily so this module (and everything that depends on it) stays importable
  when the package isn't installed.

- ``HashingEmbeddingProvider`` — a deterministic, offline, stdlib-only provider
  used for local runs and the test suite. It uses signed feature hashing
  (a real technique), so identical text yields identical vectors and text that
  shares tokens yields similar vectors. It does NOT capture deep semantics the
  way ``text-embedding-v4`` does (two paraphrases with no shared words won't
  match) — it exists so the cache mechanics can be exercised without a network.
"""
from __future__ import annotations

import hashlib
import re
from typing import List, Protocol, runtime_checkable

from app import config

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Anything that can turn text into a fixed-length vector."""

    def embed(self, text: str) -> List[float]:
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbeddingProvider:
    """Offline, deterministic embeddings via signed feature hashing."""

    def __init__(self, dim: int = config.EMBED_DIM):
        self.dim = dim

    def _bucket_and_sign(self, token: str) -> tuple[int, float]:
        # blake2b (not the salted built-in hash()) so results are stable across
        # processes — essential for a cache that must match on restart.
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        h = int.from_bytes(digest, "big")
        bucket = h % self.dim
        sign = 1.0 if (h >> 1) & 1 == 0 else -1.0
        return bucket, sign

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for token in _tokenize(text):
            bucket, sign = self._bucket_and_sign(token)
            vec[bucket] += sign
        # L2-normalise so cosine similarity is just a dot product and identical
        # text scores exactly 1.0.
        length = sum(v * v for v in vec) ** 0.5
        if length == 0.0:
            return vec
        return [v / length for v in vec]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class QwenEmbeddingProvider:
    """Production embeddings via Alibaba ``text-embedding-v4``."""

    def __init__(self, client=None, model: str = config.EMBED_MODEL, dim: int = config.EMBED_DIM):
        self._client = client
        self.model = model
        self.dim = dim

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy: only needed on the live path

            self._client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.BASE_URL)
        return self._client

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        resp = self._get_client().embeddings.create(
            model=self.model, input=texts, dimensions=self.dim
        )
        return [item.embedding for item in resp.data]

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

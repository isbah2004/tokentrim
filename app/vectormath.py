"""Small, dependency-free vector helpers.

Kept in pure Python (no numpy) so every module that needs cosine similarity —
the in-memory cache store and the RAG reranker — stays importable and testable
without third-party packages.
"""
from __future__ import annotations

import math
from typing import Sequence


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity in [-1, 1]. Returns 0.0 if either vector is all zeros
    (an empty embedding) rather than dividing by zero."""
    na, nb = norm(a), norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)

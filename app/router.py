"""Layer 3 — Model Router.

Match the model to the difficulty of the question. Alibaba positions the three
tiers as: Max for complex multi-step tasks, Plus as the balanced default, Flash
for simple fast responses. This layer automates that decision.

The MVP scorer is a cheap, instant, zero-token heuristic — free, deterministic,
and nothing to break live in front of judges. Swapping in a Flash-based
classifier once there's real traffic to tune against is the documented v2 path.
"""
from __future__ import annotations

from dataclasses import dataclass

from app import config

# Rough multiplier for "what the input would have been WITHOUT compression",
# used only for the dashboard's naive baseline. Derived conservatively from the
# build guide's worked example (8,200 -> 3,100 input tokens ≈ 2.6x); the
# pipeline passes real uncompressed counts when it has them, which is exact.
UNCOMPRESSED_FACTOR = 2.6

HARD_SIGNALS = ["compare", "analyze", "why", "explain step by step", "design", "debug"]


@dataclass
class RoutingDecision:
    model: str
    reason: str
    difficulty: float


def score_difficulty(query: str, rag_chunk_count: int, history_len: int) -> float:
    """Cheap heuristic difficulty score in [0, 1]."""
    score = 0.0
    word_count = len(query.split())

    score += min(word_count / 40, 1.0) * 0.4       # longer questions skew harder
    score += min(rag_chunk_count / 5, 1.0) * 0.3   # more retrieved context skews harder
    score += min(history_len / 10, 1.0) * 0.1      # deep conversations skew harder

    # Sentence count (multi-part questions are harder)
    sentence_count = query.count('.') + query.count('?') + query.count('!')
    score += min(sentence_count / 5, 1.0) * 0.15

    # Code presence (code questions are harder)
    if any(tok in query for tok in ['```', 'def ', 'class ', 'SELECT ', 'function']):
        score += 0.15

    lowered = query.lower()
    if any(sig in lowered for sig in HARD_SIGNALS):
        score += 0.2

    return min(score, 1.0)


def pick_model(query: str, rag_chunk_count: int, history_len: int) -> RoutingDecision:
    score = score_difficulty(query, rag_chunk_count, history_len)
    if score < config.ROUTER_SIMPLE_MAX:
        return RoutingDecision(config.MODEL_FLASH, f"difficulty={score:.2f} -> simple", score)
    if score < config.ROUTER_MEDIUM_MAX:
        return RoutingDecision(config.MODEL_PLUS, f"difficulty={score:.2f} -> medium", score)
    return RoutingDecision(config.MODEL_MAX, f"difficulty={score:.2f} -> complex", score)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of a call, from the config pricing table (per 1M tokens)."""
    price = config.PRICING[model]
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


def naive_cost(
    input_tokens: int,
    output_tokens: int,
    uncompressed_input_tokens: int | None = None,
    model: str = config.MODEL_MAX,
) -> float:
    """Cost had this request gone uncompressed to the flagship — the honest
    'do nothing' baseline for the savings dashboard.

    If ``uncompressed_input_tokens`` is known (the pipeline can measure it),
    it's used directly; otherwise the input is scaled by ``UNCOMPRESSED_FACTOR``.
    """
    if uncompressed_input_tokens is None:
        uncompressed_input_tokens = int(input_tokens * UNCOMPRESSED_FACTOR)
    return estimate_cost(model, uncompressed_input_tokens, output_tokens)

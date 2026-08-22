"""Tune the semantic-cache similarity threshold with data, not a guess.

The single easiest thing for a judge to poke at is "what if I ask it slightly
differently?" — so measure it. This prints cosine similarities for labelled
question pairs: paraphrases that SHOULD share a cached answer, and distractors
that should NOT. It then suggests a threshold that separates the two.

Uses the live text-embedding-v4 when openai + DASHSCOPE_API_KEY are available
(the numbers that matter for the demo), otherwise the offline hashing embedder.

    python scripts/tune_threshold.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config
from app.vectormath import cosine_similarity

# (question_a, question_b, should_hit)
PAIRS = [
    ("what are your opening hours", "when are you open", True),
    ("how do I reset my password", "I forgot my password, how do I change it", True),
    ("do you offer refunds", "what is your refund policy", True),
    ("what are your opening hours", "do you ship internationally", False),
    ("how do I reset my password", "what payment methods do you accept", False),
]


def _get_embedder():
    try:
        import openai  # noqa: F401

        if config.DASHSCOPE_API_KEY:
            from app.embeddings import QwenEmbeddingProvider

            return QwenEmbeddingProvider(), "text-embedding-v4 (live)"
    except ModuleNotFoundError:
        pass
    from app.embeddings import HashingEmbeddingProvider

    return HashingEmbeddingProvider(), "hashing embedder (offline fallback)"


def main() -> int:
    embedder, label = _get_embedder()
    print(f"Embedder: {label}\n")

    dup_sims, distractor_sims = [], []
    for a, b, should_hit in PAIRS:
        sim = cosine_similarity(embedder.embed(a), embedder.embed(b))
        (dup_sims if should_hit else distractor_sims).append(sim)
        kind = "paraphrase " if should_hit else "unrelated  "
        print(f"  [{kind}] sim={sim:0.3f}   {a!r}  <->  {b!r}")

    print()
    if dup_sims and distractor_sims:
        lo, hi = max(distractor_sims), min(dup_sims)
        if hi > lo:
            print(f"Paraphrases as low as {hi:0.3f}; distractors as high as {lo:0.3f}.")
            print(f"Suggested threshold ~ {(_hi := (hi + lo) / 2):0.3f} "
                  f"(current config: {config.CACHE_SIMILARITY_THRESHOLD}).")
        else:
            print("Classes overlap with this embedder — the offline fallback can't "
                  "separate paraphrases; re-run on the live text-embedding-v4 path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Aggregate metrics for the evaluation harness."""
from __future__ import annotations

from typing import Any, Dict, List


def tier_accuracy(results: List[Dict[str, Any]]) -> float:
    """Fraction of non-limitation cases where model_used == expected_model_tier."""
    eligible = [
        r for r in results
        if r.get("expected_model_tier") and not r.get("known_limitation")
    ]
    if not eligible:
        return 1.0  # vacuously true
    correct = sum(
        1 for r in eligible if r.get("model_used") == r["expected_model_tier"]
    )
    return correct / len(eligible)


def cache_hit_f1(results: List[Dict[str, Any]]) -> float:
    """F1 over cache hit predictions (non-limitation cases only).

    ``cache_hit_after_warmup`` is the expected label (True/False/None).
    None means "don't evaluate cache for this case".
    """
    eligible = [
        r for r in results
        if r.get("cache_hit_after_warmup") is not None and not r.get("known_limitation")
    ]
    if not eligible:
        return 1.0

    tp = sum(1 for r in eligible if r["cache_hit_after_warmup"] and r.get("actual_cached"))
    fp = sum(1 for r in eligible if not r["cache_hit_after_warmup"] and r.get("actual_cached"))
    fn = sum(1 for r in eligible if r["cache_hit_after_warmup"] and not r.get("actual_cached"))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def avg_compression_ratio(results: List[Dict[str, Any]]) -> float:
    """Average uncompressed/compressed token ratio across non-cached, non-limitation cases."""
    eligible = [
        r for r in results
        if not r.get("actual_cached") and not r.get("known_limitation")
        and r.get("compression_ratio") is not None
    ]
    if not eligible:
        return 1.0
    return sum(r["compression_ratio"] for r in eligible) / len(eligible)


def avg_savings_pct(results: List[Dict[str, Any]]) -> float:
    """Average (naive_cost - actual_cost) / naive_cost across non-limitation cases."""
    eligible = [
        r for r in results
        if not r.get("known_limitation") and r.get("naive_cost_usd", 0) > 0
    ]
    if not eligible:
        return 0.0
    savings = [
        (r["naive_cost_usd"] - r.get("cost_usd", 0)) / r["naive_cost_usd"]
        for r in eligible
    ]
    return sum(savings) / len(savings)


def avg_judge_score(results: List[Dict[str, Any]]) -> float:
    """Average judge overall score across all cases (including known limitations)."""
    scores = [r["judge_score"]["overall"] for r in results if "judge_score" in r]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def known_limitations_count(results: List[Dict[str, Any]]) -> int:
    """Count how many cases are flagged known_limitation."""
    return sum(1 for r in results if r.get("known_limitation"))

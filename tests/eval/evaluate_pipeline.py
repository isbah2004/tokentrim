"""CLI evaluation harness for TokenTrim.

Usage (offline):
    python -m tests.eval.evaluate_pipeline \
        --dataset tests/eval/datasets/golden_v1.jsonl \
        --output eval-report.json --assert-thresholds

Usage (live):
    TOKENTRIM_JUDGE_LIVE=1 DASHSCOPE_API_KEY=... \
    python -m tests.eval.evaluate_pipeline \
        --dataset tests/eval/datasets/golden_v1.jsonl \
        --output eval-live-report.json --assert-thresholds
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make sure the repo root is on sys.path when run as a module
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.cache import InMemoryVectorStore, SemanticCache
from app.embeddings import HashingEmbeddingProvider
from app.pipeline import Gateway
from tests.eval.dataset_loader import EvalCase, load_dataset
from tests.eval.fakes import MappingFakeChatModel
from tests.eval.judge import make_judge
from tests.eval.metrics import (
    avg_compression_ratio,
    avg_judge_score,
    avg_savings_pct,
    cache_hit_f1,
    known_limitations_count,
    tier_accuracy,
)


# --------------------------------------------------------------------------- #
#  Offline thresholds
# --------------------------------------------------------------------------- #
OFFLINE_THRESHOLDS = {
    "tier_accuracy": 0.85,
    "cache_hit_f1": 0.80,
    "avg_compression_ratio": 1.2,
    "avg_savings_pct": 0.0,   # > 0
    "avg_judge_overall": 0.70,
}

LIVE_THRESHOLDS = {
    "tier_accuracy": 0.80,
    "cache_hit_f1": 0.70,
    "avg_judge_overall": 0.70,  # normalised from 3.5/5
}


def _build_offline_gateway(mapping: Dict[str, str]) -> Gateway:
    store = InMemoryVectorStore()
    embedder = HashingEmbeddingProvider()
    cache = SemanticCache(store=store, embedder=embedder)
    chat_model = MappingFakeChatModel(mapping=mapping)
    fd, log_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(log_path)
    return Gateway(cache=cache, chat_model=chat_model, stats_log_file=log_path)


def _prompt_content(prompt: List[Dict[str, str]]) -> str:
    return " ".join(m.get("content", "") for m in prompt)


def run_case(
    case: EvalCase,
    judge,
    live: bool = False,
) -> Dict[str, Any]:
    """Run a single eval case and return a result dict."""
    mapping = {case.query: case.golden_answer}
    if case.warmup_query:
        mapping[case.warmup_query] = case.golden_answer

    # Each case gets its own isolated gateway (fresh cache)
    gw = _build_offline_gateway(mapping)

    result: Dict[str, Any] = {
        "id": case.id,
        "category": case.category,
        "known_limitation": case.known_limitation,
        "cache_hit_after_warmup": case.cache_hit_after_warmup,
        "expected_model_tier": case.expected_model_tier,
        "findings": [],
    }

    # ── Warmup ──────────────────────────────────────────────────────────────
    if case.warmup_query:
        warmup_kwargs: Dict[str, Any] = {
            "skip_cache": case.id == "skip-cache-01",
        }
        gw.chat(case.warmup_query, **warmup_kwargs)

    # ── Evaluate ────────────────────────────────────────────────────────────
    chat_kwargs: Dict[str, Any] = {
        "history": case.history,
        "rag_chunks": case.rag_chunks,
    }
    if case.id == "forced-tier-01":
        from app import config
        chat_kwargs["forced_tier"] = config.MODEL_MAX
    if case.id == "skip-cache-01":
        chat_kwargs["skip_cache"] = True
    if case.id == "skip-compression-01":
        chat_kwargs["skip_compression"] = True

    response = gw.chat(case.query, **chat_kwargs)

    result["actual_cached"] = response.cached
    result["model_used"] = response.model_used
    result["cost_usd"] = response.cost_usd
    result["naive_cost_usd"] = response.naive_cost_usd
    result["response_text"] = response.response
    result["similarity"] = response.similarity

    # ── Compression ratio ────────────────────────────────────────────────────
    if not response.cached:
        breakdown = response.tokens.get("breakdown", {})
        u_hist = breakdown.get("uncompressed", {}).get("history", 0)
        c_hist = breakdown.get("compressed", {}).get("history", 0)
        ratio = u_hist / max(c_hist, 1) if u_hist > 0 else 1.0
        result["compression_ratio"] = ratio
    else:
        result["compression_ratio"] = None

    # ── Prompt content checks ────────────────────────────────────────────────
    trimmed_text = _prompt_content(response.trimmed_prompt)
    naive_text = _prompt_content(response.naive_prompt)

    prompt_check_pass = True
    for token in case.required_in_trimmed_prompt:
        if token not in trimmed_text:
            if case.known_limitation:
                result["findings"].append(
                    f"FINDING: '{token}' absent from trimmed_prompt (known limitation)"
                )
            else:
                prompt_check_pass = False
                result["findings"].append(
                    f"FAIL: '{token}' missing from trimmed_prompt"
                )
    for token in case.required_in_naive_prompt:
        if token not in naive_text:
            result["findings"].append(f"FAIL: '{token}' missing from naive_prompt")
            prompt_check_pass = False

    result["prompt_checks_passed"] = prompt_check_pass

    # ── Cache expectation ────────────────────────────────────────────────────
    cache_ok = True
    if case.cache_hit_after_warmup is not None:
        if case.cache_hit_after_warmup != response.cached:
            if case.known_limitation:
                result["findings"].append(
                    f"FINDING: expected cached={case.cache_hit_after_warmup}, "
                    f"got cached={response.cached} (known limitation). "
                    f"observed_similarity={response.similarity}"
                )
            else:
                cache_ok = False
                result["findings"].append(
                    f"FAIL: expected cached={case.cache_hit_after_warmup}, "
                    f"got cached={response.cached}"
                )
        if response.similarity is not None:
            result["observed_similarity"] = response.similarity
    result["cache_expectation_met"] = cache_ok

    # ── Judge ────────────────────────────────────────────────────────────────
    score = judge.score(case.query, case.golden_answer, response.response)
    result["judge_score"] = {
        "correctness": score.correctness,
        "completeness": score.completeness,
        "conciseness": score.conciseness,
        "hallucination_free": score.hallucination_free,
        "overall": score.overall,
        "explanation": score.explanation,
    }

    # ── Tier check ───────────────────────────────────────────────────────────
    if case.expected_model_tier and response.model_used:
        tier_ok = response.model_used == case.expected_model_tier
        if not tier_ok:
            result["findings"].append(
                f"FAIL: expected model={case.expected_model_tier}, got={response.model_used}"
            )

    return result


def compute_aggregate(results: List[Dict[str, Any]], live: bool) -> Dict[str, Any]:
    ta = tier_accuracy(results)
    chf1 = cache_hit_f1(results)
    acr = avg_compression_ratio(results)
    asp = avg_savings_pct(results)
    ajs = avg_judge_score(results)
    n_lim = known_limitations_count(results)
    return {
        "tier_accuracy": ta,
        "cache_hit_f1": chf1,
        "avg_compression_ratio": acr,
        "avg_savings_pct": asp,
        "avg_judge_overall": ajs,
        "known_limitations_count": n_lim,
        "total_cases": len(results),
    }


def check_thresholds(aggregate: Dict[str, Any], live: bool) -> List[str]:
    thresholds = LIVE_THRESHOLDS if live else OFFLINE_THRESHOLDS
    failures = []
    for metric, threshold in thresholds.items():
        val = aggregate.get(metric, 0.0)
        if val < threshold:
            failures.append(
                f"GATE FAIL: {metric}={val:.3f} < threshold={threshold:.3f}"
            )
    # avg_savings_pct must be > 0 (not >=)
    if not live and aggregate.get("avg_savings_pct", 0.0) <= 0:
        failures.append(
            f"GATE FAIL: avg_savings_pct={aggregate['avg_savings_pct']:.3f} must be > 0"
        )
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="TokenTrim offline evaluation harness")
    parser.add_argument("--dataset", required=True, help="Path to golden JSONL dataset")
    parser.add_argument("--output", default="eval-report.json", help="Output JSON report path")
    parser.add_argument("--assert-thresholds", action="store_true",
                        help="Exit 1 if gate thresholds not met (on unexpected failures only)")
    args = parser.parse_args(argv)

    live = os.getenv("TOKENTRIM_JUDGE_LIVE") == "1"
    judge = make_judge()
    judge_type = type(judge).__name__
    print(f"[eval] judge={judge_type}, live={live}")

    cases = load_dataset(args.dataset)
    print(f"[eval] loaded {len(cases)} cases from {args.dataset}")

    results = []
    for case in cases:
        print(f"[eval] running {case.id} ...", end=" ", flush=True)
        try:
            r = run_case(case, judge=judge, live=live)
            status = "known_limitation" if case.known_limitation else (
                "PASS" if r["prompt_checks_passed"] and r["cache_expectation_met"] else "FAIL"
            )
            print(status)
            if r["findings"]:
                for f in r["findings"]:
                    print(f"       {f}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            r = {
                "id": case.id, "category": case.category,
                "known_limitation": case.known_limitation,
                "error": str(exc),
                "prompt_checks_passed": False,
                "cache_expectation_met": False,
                "actual_cached": False,
            }
        results.append(r)

    aggregate = compute_aggregate(results, live)
    gate_failures = check_thresholds(aggregate, live) if args.assert_thresholds else []

    # Identify limitation cases that unexpectedly passed
    for r in results:
        if r.get("known_limitation") and not r.get("findings"):
            r["limitation_resolved"] = True

    report = {
        "meta": {
            "dataset": args.dataset,
            "judge": judge_type,
            "live": live,
            "total_cases": len(results),
        },
        "aggregate": aggregate,
        "gate_failures": gate_failures,
        "results": results,
    }

    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"\n[eval] report written to {args.output}")
    print(f"[eval] aggregate: {json.dumps(aggregate, indent=2)}")

    if gate_failures:
        print(f"\n[eval] GATE FAILURES ({len(gate_failures)}):")
        for f in gate_failures:
            print(f"  {f}")
        if args.assert_thresholds:
            sys.exit(1)

    print("\n[eval] PASSED (known_limitation cases are findings, not failures)")
    sys.exit(0)


if __name__ == "__main__":
    main()

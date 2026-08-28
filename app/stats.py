"""Request logging + cost aggregation for the savings dashboard.

Each request appends one JSON line to a log file; ``get_summary`` reduces the
log into the numbers the dashboard shows: total cost, the naive "do nothing"
baseline, percentage saved, and cache hit rate.

The log path is a parameter (defaulting to ``config.STATS_LOG_FILE``) so tests
can point it at a temp file.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app import config
from app.router import naive_cost as compute_naive_cost


def log_request(log_file: Optional[str] = None, **fields: Any) -> None:
    """Append one request record. Pass whatever fields you have; the pipeline
    logs: cache_hit, model, input_tokens, output_tokens, cached_tokens, cost,
    naive_cost, latency, routing_reason."""
    path = Path(log_file or config.STATS_LOG_FILE)
    fields.setdefault("timestamp", time.time())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields) + "\n")


def _row_naive_cost(row: Dict[str, Any]) -> float:
    """Baseline cost for one row: prefer an exact value logged by the pipeline,
    otherwise estimate from token counts."""
    if row.get("naive_cost") is not None:
        return float(row["naive_cost"])
    return compute_naive_cost(
        input_tokens=int(row.get("input_tokens", 0)),
        output_tokens=int(row.get("output_tokens", 0)),
    )


def get_summary(log_file: Optional[str] = None) -> Dict[str, Any]:
    path = Path(log_file or config.STATS_LOG_FILE)
    if not path.exists():
        return {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_hit_rate": 0.0,
            "total_cost_usd": 0.0,
            "estimated_naive_cost_usd": 0.0,
            "estimated_savings_usd": 0.0,
            "estimated_savings_pct": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "avg_input_tokens": 0.0,
            "models_distribution": {},
            "recent_requests": [],
        }

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(rows)
    cache_hits = sum(1 for r in rows if r.get("cache_hit"))
    total_cost = sum(float(r.get("cost", 0.0)) for r in rows)
    naive_total = sum(_row_naive_cost(r) for r in rows)
    total_input = sum(int(r.get("input_tokens", 0)) for r in rows)
    total_output = sum(int(r.get("output_tokens", 0)) for r in rows)

    generated = max(total - cache_hits, 0)  # requests that actually hit a model
    savings = naive_total - total_cost

    models_distribution = {}
    for r in rows:
        model = r.get("model")
        if model:
            models_distribution[model] = models_distribution.get(model, 0) + 1
            
    recent_requests = rows[-10:]
    recent_requests.reverse()

    return {
        "total_requests": total,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / total, 3) if total else 0.0,
        "total_cost_usd": round(total_cost, 6),
        "estimated_naive_cost_usd": round(naive_total, 6),
        "estimated_savings_usd": round(savings, 6),
        "estimated_savings_pct": round((savings / naive_total) * 100, 1) if naive_total else 0.0,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "avg_input_tokens": round(total_input / generated, 1) if generated else 0.0,
        "models_distribution": models_distribution,
        "recent_requests": recent_requests,
    }

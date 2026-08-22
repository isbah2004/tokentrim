"""Populate the stats log with a realistic traffic mix so the dashboard has
numbers to show (and screenshots to take) before a demo.

Runs fully offline against the local fakes — no key or database required.

    python scripts/simulate_demo.py            # append to the default stats log
    python scripts/simulate_demo.py --reset    # clear the log first
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, stats
from app.cache import InMemoryVectorStore, SemanticCache
from app.embeddings import HashingEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import FakeChatModel

# A scripted mix: simple FAQ (with repeats -> cache hits) + a few hard ones.
SCRIPT = [
    ("what are your opening hours", [], []),
    ("what are your opening hours", [], []),        # exact repeat -> hit
    ("do you offer student discounts", [], []),
    ("do you offer student discounts", [], []),     # repeat -> hit
    ("how do I track my order", [], []),
    ("what payment methods do you accept", [], []),
    ("how do I track my order", [], []),            # repeat -> hit
    (
        "please analyze and compare your enterprise and pro plans and explain "
        "which is better for a 200-person company " + "detail " * 30,
        [{"role": "user", "content": "earlier context " * 20} for _ in range(8)],
        [f"pricing doc chunk {i}" for i in range(5)],
    ),
    (
        "debug why my integration returns a 401 after refreshing the token " + "trace " * 20,
        [{"role": "user", "content": "log line " * 15} for _ in range(6)],
        [f"api doc chunk {i}" for i in range(4)],
    ),
]


def main(argv: list[str]) -> int:
    log_file = config.STATS_LOG_FILE
    if "--reset" in argv and os.path.exists(log_file):
        os.remove(log_file)
        print(f"cleared {log_file}")

    gateway = Gateway(
        cache=SemanticCache(InMemoryVectorStore(), HashingEmbeddingProvider()),
        chat_model=FakeChatModel(answer="(demo answer)"),
        stats_log_file=log_file,
    )

    for query, history, rag in SCRIPT:
        resp = gateway.chat(query, history=history, rag_chunks=rag)
        tag = "CACHE HIT" if resp.cached else (resp.model_used or "?")
        print(f"  [{tag:>13}] ${resp.cost_usd:.6f} (baseline ${resp.naive_cost_usd:.6f})  {query[:44]!r}")

    print("\n=== summary ===")
    for k, v in stats.get_summary(log_file).items():
        print(f"  {k}: {v}")
    print(f"\nStart the server and open the dashboard to view: uvicorn app.main:app")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

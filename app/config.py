"""Central configuration for TokenTrim.

Everything tunable — model IDs, the pricing table, routing thresholds, and the
cache similarity cutoff — lives here so there is exactly one place to edit when
Alibaba changes prices or you want to retune the gateway.

Values can be overridden via environment variables (see .env.example). The
defaults are Alibaba Cloud Model Studio, Singapore/International list prices as
of August 2026. ALWAYS re-verify against the live pricing page before a demo:
https://www.alibabacloud.com/help/en/model-studio/model-pricing
"""
from __future__ import annotations

import os

# Load a local .env if python-dotenv is available; a no-op otherwise so that
# importing config never hard-depends on an optional package.
try:  # pragma: no cover - trivial optional import
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:  # pragma: no cover
    pass


# --- Model Studio connection ---------------------------------------------
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# Singapore/International endpoint (carries the pricing used throughout).
# For mainland China, set TOKENTRIM_BASE_URL to the .aliyuncs.com endpoint.
BASE_URL = os.getenv(
    "TOKENTRIM_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# --- Embeddings -----------------------------------------------------------
EMBED_MODEL = os.getenv("TOKENTRIM_EMBED_MODEL", "text-embedding-v4")
# 768 keeps the pgvector index small and lookups cheap; text-embedding-v4
# supports smaller dims for cost-sensitive setups.
EMBED_DIM = int(os.getenv("TOKENTRIM_EMBED_DIM", "768"))

# --- Model tiers ----------------------------------------------------------
MODEL_FLASH = "qwen3.5-flash"  # cheap tier: simple, fast questions
MODEL_PLUS = "qwen-plus"       # balanced default for most scenarios
MODEL_MAX = "qwen3.7-max"      # flagship: complex, multi-step reasoning

# --- Pricing: USD per 1,000,000 tokens -----------------------------------
# Alibaba Cloud Model Studio, Singapore/International list prices, Aug 2026.
PRICING = {
    MODEL_FLASH: {"input": 0.10, "output": 0.40},
    MODEL_PLUS: {"input": 0.40, "output": 1.20},
    MODEL_MAX: {"input": 2.50, "output": 7.50},
}

# --- Routing thresholds (difficulty score in [0, 1]) ---------------------
ROUTER_SIMPLE_MAX = float(os.getenv("TOKENTRIM_ROUTER_SIMPLE_MAX", "0.35"))
ROUTER_MEDIUM_MAX = float(os.getenv("TOKENTRIM_ROUTER_MEDIUM_MAX", "0.70"))

# --- Semantic cache -------------------------------------------------------
# Cosine-similarity cutoff for treating a stored answer as a hit. Tune against
# real near-duplicate question pairs before locking it in (see docs/PHASE_4).
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("TOKENTRIM_CACHE_THRESHOLD", "0.92"))

# --- Stats ----------------------------------------------------------------
STATS_LOG_FILE = os.getenv("TOKENTRIM_STATS_FILE", "tokentrim_stats.jsonl")


def validate() -> list[str]:
    """Return a list of human-readable config problems (empty means all good).

    Called by the config unit test and worth wiring into app startup so a
    typo in an env override fails loudly instead of skewing routing silently.
    """
    problems: list[str] = []
    if not (0.0 < CACHE_SIMILARITY_THRESHOLD <= 1.0):
        problems.append("CACHE_SIMILARITY_THRESHOLD must be in (0, 1].")
    if not (0.0 < ROUTER_SIMPLE_MAX < ROUTER_MEDIUM_MAX < 1.0):
        problems.append("Require 0 < ROUTER_SIMPLE_MAX < ROUTER_MEDIUM_MAX < 1.")
    if EMBED_DIM <= 0:
        problems.append("EMBED_DIM must be a positive integer.")
    for tier in (MODEL_FLASH, MODEL_PLUS, MODEL_MAX):
        price = PRICING.get(tier)
        if not price or "input" not in price or "output" not in price:
            problems.append(f"Missing input/output pricing for model tier {tier!r}.")
    return problems

"""The gateway pipeline: cache -> compress -> route -> generate -> log.

``Gateway`` ties the three layers together. It takes its collaborators as
constructor arguments (a ``SemanticCache`` and a ``ChatModel``), so the exact
same class runs against real Qwen + pgvector in production and against offline
fakes in the test suite. FastAPI (``app.main``) is a thin HTTP shell over this.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app import config
from app.cache import SemanticCache
from app.compressor import Message, build_prompt, compress_history
from app.qwen_client import ChatModel
from app.router import estimate_cost, naive_cost, pick_model
from app.stats import log_request
from app.tokens import estimate_message_tokens

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass
class ChatResponse:
    response: str
    cached: bool
    cost_usd: float
    tokens: Dict[str, int]
    latency_ms: float
    model_used: Optional[str] = None
    routing_reason: Optional[str] = None
    similarity: Optional[float] = None
    naive_cost_usd: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Gateway:
    def __init__(
        self,
        cache: SemanticCache,
        chat_model: ChatModel,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        stats_log_file: Optional[str] = None,
    ):
        self.cache = cache
        self.chat_model = chat_model
        self.system_prompt = system_prompt
        self.stats_log_file = stats_log_file  # None -> config.STATS_LOG_FILE

    def chat(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        rag_chunks: Optional[List[str]] = None,
    ) -> ChatResponse:
        history = history or []
        rag_chunks = rag_chunks or []
        t0 = time.perf_counter()

        # --- Layer 1: semantic cache -----------------------------------
        hit = self.cache.lookup(query)
        if hit is not None:
            latency_ms = (time.perf_counter() - t0) * 1000
            # A hit still "saves" whatever a full uncompressed flagship call
            # would have cost; approximate that from the raw request so the
            # dashboard credits the cache honestly.
            baseline = self._baseline_for_cache_hit(query, history, rag_chunks)
            log_request(
                log_file=self.stats_log_file,
                cache_hit=True,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cached_tokens=0,
                cost=0.0,
                naive_cost=baseline,
                latency_ms=latency_ms,
                routing_reason="cache_hit",
            )
            return ChatResponse(
                response=hit.response,
                cached=True,
                cost_usd=0.0,
                tokens={"input": 0, "output": 0},
                latency_ms=latency_ms,
                similarity=hit.similarity,
                naive_cost_usd=baseline,
            )

        # --- Layer 2: context compression ------------------------------
        msg_history = [Message(role=m["role"], content=m["content"]) for m in history]
        compressed_history = compress_history(msg_history)
        messages = build_prompt(self.system_prompt, compressed_history, rag_chunks, query)

        # The uncompressed prompt (full history, untrimmed) is what a naive app
        # would have sent; we use its size only to scale the baseline.
        uncompressed_messages = build_prompt(self.system_prompt, msg_history, rag_chunks, query)
        compressed_est = estimate_message_tokens(messages)
        uncompressed_est = estimate_message_tokens(uncompressed_messages)
        ratio = uncompressed_est / max(compressed_est, 1)

        # --- Layer 3: model routing ------------------------------------
        decision = pick_model(query, len(rag_chunks), len(history))
        result = self.chat_model.generate(decision.model, messages)

        cost = estimate_cost(decision.model, result.prompt_tokens, result.completion_tokens)
        # Baseline: the same request uncompressed, on the flagship tier.
        uncompressed_input_tokens = round(result.prompt_tokens * ratio)
        baseline = naive_cost(
            input_tokens=result.prompt_tokens,
            output_tokens=result.completion_tokens,
            uncompressed_input_tokens=uncompressed_input_tokens,
            model=config.MODEL_MAX,
        )

        self.cache.store_answer(query, result.text)
        latency_ms = (time.perf_counter() - t0) * 1000

        log_request(
            log_file=self.stats_log_file,
            cache_hit=False,
            model=decision.model,
            input_tokens=result.prompt_tokens,
            output_tokens=result.completion_tokens,
            cached_tokens=result.cached_tokens,
            cost=cost,
            naive_cost=baseline,
            latency_ms=latency_ms,
            routing_reason=decision.reason,
        )

        return ChatResponse(
            response=result.text,
            cached=False,
            cost_usd=round(cost, 6),
            tokens={"input": result.prompt_tokens, "output": result.completion_tokens},
            latency_ms=latency_ms,
            model_used=decision.model,
            routing_reason=decision.reason,
            naive_cost_usd=round(baseline, 6),
        )

    def _baseline_for_cache_hit(
        self, query: str, history: List[Dict[str, str]], rag_chunks: List[str]
    ) -> float:
        """Estimate the flagship, uncompressed cost this cache hit avoided."""
        msg_history = [Message(role=m["role"], content=m["content"]) for m in history]
        uncompressed_messages = build_prompt(self.system_prompt, msg_history, rag_chunks, query)
        input_tokens = estimate_message_tokens(uncompressed_messages)
        # Assume a modest answer length for the avoided generation.
        return naive_cost(
            input_tokens=input_tokens,
            output_tokens=0,
            uncompressed_input_tokens=input_tokens,
            model=config.MODEL_MAX,
        )

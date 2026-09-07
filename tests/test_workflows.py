"""Workflow-level integration tests for the Gateway pipeline.

Each test wires a full Gateway with offline fakes (InMemoryVectorStore +
HashingEmbeddingProvider + FakeChatModel + temp stats file) and exercises the
full cache → compress → route → generate path end-to-end.

No network, no database, no model keys required — all offline.
"""
import os
import tempfile
import unittest

from app.cache import InMemoryVectorStore, SemanticCache
from app.embeddings import HashingEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import FakeChatModel


def _make_gateway(answer: str = "test answer", threshold: float = 0.92) -> Gateway:
    """Construct a fully-offline Gateway for testing."""
    store = InMemoryVectorStore()
    embedder = HashingEmbeddingProvider()
    cache = SemanticCache(store=store, embedder=embedder, similarity_threshold=threshold)
    chat_model = FakeChatModel(answer=answer)
    fd, log_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(log_path)
    return Gateway(cache=cache, chat_model=chat_model, stats_log_file=log_path)


class CacheMissRegressionTest(unittest.TestCase):
    """§1 regression: cache miss must NOT raise UnboundLocalError."""

    def test_cache_miss_no_unbound_local_error(self):
        """First query on an empty cache must complete without crashing."""
        gw = _make_gateway()
        # This used to raise UnboundLocalError: latency_ms referenced before assignment
        result = gw.chat("what are the store hours?")
        self.assertFalse(result.cached)
        self.assertIsNotNone(result.response)
        self.assertGreater(result.latency_ms, 0)

    def test_second_cache_miss_distinct_query_no_error(self):
        """Two distinct queries on a near-empty cache should both complete."""
        gw = _make_gateway()
        r1 = gw.chat("hello world")
        r2 = gw.chat("completely different question about databases")
        self.assertFalse(r1.cached)
        self.assertFalse(r2.cached)


class CacheHitPathTest(unittest.TestCase):
    """Second identical query must hit the cache."""

    def test_cache_hit_path(self):
        gw = _make_gateway(answer="cached answer")
        q = "what is the return policy"
        gw.chat(q)
        result = gw.chat(q)
        self.assertTrue(result.cached)
        self.assertEqual(result.cost_usd, 0.0)
        self.assertAlmostEqual(result.similarity, 1.0, places=5)
        self.assertEqual(result.response, "cached answer")

    def test_cache_hit_tokens_are_zero(self):
        gw = _make_gateway()
        q = "repeat query"
        gw.chat(q)
        result = gw.chat(q)
        self.assertTrue(result.cached)
        self.assertEqual(result.tokens["input"], 0)
        self.assertEqual(result.tokens["output"], 0)

    def test_cache_hit_naive_cost_greater_than_zero(self):
        """Even a cache hit should report a positive naive_cost_usd (savings)."""
        gw = _make_gateway()
        q = "how much does shipping cost"
        gw.chat(q)
        result = gw.chat(q)
        self.assertTrue(result.cached)
        self.assertGreater(result.naive_cost_usd, 0.0)


class SkipCacheFlagTest(unittest.TestCase):
    """skip_cache=True must bypass both lookup and store."""

    def test_skip_cache_bypasses_lookup(self):
        gw = _make_gateway()
        q = "do you offer discounts"
        gw.chat(q)
        result = gw.chat(q, skip_cache=True)
        self.assertFalse(result.cached)

    def test_skip_cache_does_not_store(self):
        gw = _make_gateway()
        q = "what is your warranty"
        gw.chat(q, skip_cache=True)
        result = gw.chat(q)
        self.assertFalse(result.cached)


class CompressionPathTest(unittest.TestCase):
    """Compression should reduce history tokens."""

    def _long_history(self, n: int = 8):
        turns = []
        for i in range(n):
            turns.append({"role": "user", "content": f"user message number {i} with some extra words to pad it out"})
            turns.append({"role": "assistant", "content": f"assistant reply number {i} with more words to make it longer"})
        return turns

    def test_compression_path_saves_tokens(self):
        gw = _make_gateway()
        history = self._long_history(6)
        result = gw.chat("what is your final answer", history=history)
        self.assertFalse(result.cached)
        uncompressed_hist = result.tokens["breakdown"]["uncompressed"]["history"]
        compressed_hist = result.tokens["breakdown"]["compressed"]["history"]
        self.assertLess(compressed_hist, uncompressed_hist,
                        "Compression should reduce history token count")

    def test_naive_cost_greater_than_actual_cost(self):
        gw = _make_gateway()
        history = self._long_history(6)
        result = gw.chat("summarise our conversation", history=history)
        self.assertGreater(result.naive_cost_usd, result.cost_usd,
                           "naive_cost_usd should exceed actual cost_usd when compression fires")


class SkipCompressionTest(unittest.TestCase):
    """skip_compression=True must preserve history verbatim."""

    def test_skip_compression_preserves_history(self):
        history = [
            {"role": "user", "content": "turn one"},
            {"role": "assistant", "content": "turn two"},
            {"role": "user", "content": "turn three"},
            {"role": "assistant", "content": "turn four"},
            {"role": "user", "content": "turn five"},
            {"role": "assistant", "content": "turn six"},
        ]
        gw = _make_gateway()
        result = gw.chat("final query", history=history, skip_compression=True)
        uncompressed_hist = result.tokens["breakdown"]["uncompressed"]["history"]
        compressed_hist = result.tokens["breakdown"]["compressed"]["history"]
        self.assertEqual(uncompressed_hist, compressed_hist,
                         "skip_compression should keep history token count identical")


class ForcedTierTest(unittest.TestCase):
    """forced_tier must override the router's decision."""

    def test_forced_tier_overrides_router(self):
        from app import config
        gw = _make_gateway()
        result = gw.chat(
            "analyze compare why debug explain step by step this complex system",
            forced_tier=config.MODEL_FLASH,
        )
        self.assertEqual(result.model_used, config.MODEL_FLASH)
        self.assertEqual(result.routing_reason, "forced_by_user")

    def test_forced_max_tier(self):
        from app import config
        gw = _make_gateway()
        result = gw.chat("hello", forced_tier=config.MODEL_MAX)
        self.assertEqual(result.model_used, config.MODEL_MAX)


class RAGRerankPathTest(unittest.TestCase):
    """RAG chunks should appear in the trimmed prompt."""

    def test_rag_chunks_present_in_trimmed_prompt(self):
        gw = _make_gateway()
        chunks = ["chunk alpha", "chunk beta", "chunk gamma", "chunk delta"]
        result = gw.chat("what does chunk alpha say", rag_chunks=chunks)
        trimmed_content = " ".join(m.get("content", "") for m in result.trimmed_prompt)
        self.assertTrue(
            any(c in trimmed_content for c in chunks),
            "At least one RAG chunk should appear in the trimmed prompt"
        )

    def test_empty_rag_chunks_no_context_header(self):
        gw = _make_gateway()
        result = gw.chat("simple question", rag_chunks=[])
        system_msg = result.trimmed_prompt[0]["content"]
        self.assertNotIn("Context:", system_msg)


class RoutingTest(unittest.TestCase):
    """Router should pick flash for simple queries and max for complex ones."""

    def test_simple_query_routes_to_flash(self):
        from app import config
        gw = _make_gateway()
        result = gw.chat("hi")
        self.assertEqual(result.model_used, config.MODEL_FLASH)

    def test_complex_query_routes_to_max(self):
        from app import config
        gw = _make_gateway()
        result = gw.chat(
            "Please analyze and compare the design patterns used in "
            "microservices vs monolith architectures. Explain step by step "
            "why one might choose each approach. Debug the tradeoffs "
            "in terms of scalability, maintainability, and team velocity. "
            "Also, consider the database aspect! How does it work? "
            "What is the design?"
        )
        self.assertEqual(result.model_used, config.MODEL_MAX)

    def test_routing_reason_present(self):
        gw = _make_gateway()
        result = gw.chat("what time is it")
        self.assertIsNotNone(result.routing_reason)
        self.assertIn("difficulty=", result.routing_reason)


class NaiveAndTrimmedPromptShapeTest(unittest.TestCase):
    """naive_prompt and trimmed_prompt must be well-formed lists of dicts."""

    def test_prompts_are_lists_of_dicts(self):
        gw = _make_gateway()
        result = gw.chat("what is your refund policy",
                         history=[{"role": "user", "content": "hello"}])
        self.assertIsInstance(result.naive_prompt, list)
        self.assertIsInstance(result.trimmed_prompt, list)
        for msg in result.naive_prompt + result.trimmed_prompt:
            self.assertIn("role", msg)
            self.assertIn("content", msg)

    def test_last_message_is_user_query(self):
        gw = _make_gateway()
        result = gw.chat("my final question")
        self.assertEqual(result.trimmed_prompt[-1]["role"], "user")
        self.assertEqual(result.trimmed_prompt[-1]["content"], "my final question")


if __name__ == "__main__":
    unittest.main()

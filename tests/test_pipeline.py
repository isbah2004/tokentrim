import os
import tempfile
import unittest

from app import config, stats
from app.cache import InMemoryVectorStore, SemanticCache
from app.embeddings import HashingEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import FakeChatModel


class GatewayPipelineTests(unittest.TestCase):
    def setUp(self):
        fd, self.log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.log)
        self.addCleanup(lambda: os.path.exists(self.log) and os.remove(self.log))
        self.gateway = Gateway(
            cache=SemanticCache(InMemoryVectorStore(), HashingEmbeddingProvider(), 0.92),
            chat_model=FakeChatModel(answer="the cached answer"),
            stats_log_file=self.log,
        )

    def test_first_call_generates(self):
        resp = self.gateway.chat("what are your opening hours today")
        self.assertFalse(resp.cached)
        self.assertIsNotNone(resp.model_used)
        self.assertGreater(resp.cost_usd, 0.0)
        self.assertGreaterEqual(resp.naive_cost_usd, resp.cost_usd)
        self.assertGreater(resp.tokens["input"], 0)
        self.assertGreaterEqual(resp.latency_ms, 0.0)

    def test_repeat_query_hits_cache(self):
        self.gateway.chat("what are your opening hours today")
        resp = self.gateway.chat("what are your opening hours today")
        self.assertTrue(resp.cached)
        self.assertEqual(resp.response, "the cached answer")
        self.assertEqual(resp.cost_usd, 0.0)
        self.assertAlmostEqual(resp.similarity, 1.0, places=6)

    def test_simple_query_routes_cheap(self):
        resp = self.gateway.chat("hi")
        self.assertEqual(resp.model_used, config.MODEL_FLASH)

    def test_complex_query_routes_flagship(self):
        history = [{"role": "user", "content": f"turn {i}"} for i in range(10)]
        rag = [f"chunk {i}" for i in range(5)]
        query = "please analyze and compare " + " ".join(["token"] * 50)
        resp = self.gateway.chat(query, history=history, rag_chunks=rag)
        self.assertEqual(resp.model_used, config.MODEL_MAX)

    def test_compression_makes_baseline_exceed_actual(self):
        history = [{"role": "user", "content": "old context " * 20} for _ in range(8)]
        resp = self.gateway.chat("a short follow up question", history=history)
        # history is trimmed, so the uncompressed flagship baseline should be
        # clearly larger than the actual optimized cost.
        self.assertGreater(resp.naive_cost_usd, resp.cost_usd)

    def test_stats_reflect_traffic(self):
        self.gateway.chat("question one about pricing")   # generate
        self.gateway.chat("question one about pricing")   # cache hit
        self.gateway.chat("a different question entirely")  # generate
        summary = stats.get_summary(self.log)
        self.assertEqual(summary["total_requests"], 3)
        self.assertEqual(summary["cache_hits"], 1)
        self.assertGreater(summary["estimated_savings_pct"], 0.0)
        self.assertGreater(summary["estimated_naive_cost_usd"], summary["total_cost_usd"])


if __name__ == "__main__":
    unittest.main()

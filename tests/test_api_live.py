"""Live API integration tests — only run when TOKENTRIM_LIVE=1 and keys are set.

These tests exercise the real Qwen models via Model Studio. They are skipped
completely in CI and offline environments.
"""
import os
import tempfile
import unittest

from app import config

_LIVE = os.getenv("TOKENTRIM_LIVE") == "1" and bool(config.DASHSCOPE_API_KEY)

try:
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient
    _HAVE_HTTP_STACK = True
except Exception:
    _HAVE_HTTP_STACK = False


@unittest.skipUnless(_LIVE and _HAVE_HTTP_STACK, "TOKENTRIM_LIVE=1 and DASHSCOPE_API_KEY required")
class LiveApiTests(unittest.TestCase):
    """Live integration tests: real model calls, real costs."""

    @classmethod
    def setUpClass(cls):
        import app.main as main
        fd, cls.log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(cls.log)
        main.gateway.stats_log_file = cls.log
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.log):
            os.remove(cls.log)

    def test_live_generation_has_positive_cost(self):
        res = self.client.post("/chat", json={"query": "What is the capital of Japan?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["cached"])
        self.assertGreater(data["cost_usd"], 0.0)

    def test_live_cache_hit_on_repeat(self):
        q = "What is the speed of light in metres per second?"
        first = self.client.post("/chat", json={"query": q})
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["cached"])

        second = self.client.post("/chat", json={"query": q})
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["cached"])
        self.assertEqual(second.json()["cost_usd"], 0.0)

    def test_live_stats_endpoint(self):
        res = self.client.get("/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_requests", data)
        self.assertIn("total_savings_usd", data)

    def test_live_response_is_non_empty(self):
        res = self.client.post("/chat", json={"query": "Say hello in one word."})
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.json()["response"]), 0)


if __name__ == "__main__":
    unittest.main()

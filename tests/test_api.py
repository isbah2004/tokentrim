"""HTTP-level tests for the FastAPI gateway.

These require fastapi + httpx (FastAPI's TestClient dependency). When those
aren't installed — e.g. the offline/dev environment where only the stdlib is
available — the whole class skips cleanly. The gateway's behaviour is covered
regardless by tests/test_pipeline.py, which exercises the same Gateway object
without HTTP.
"""
import os
import tempfile
import unittest

try:
    import fastapi  # noqa: F401
    import httpx  # noqa: F401
    from fastapi.testclient import TestClient

    _HAVE_HTTP_STACK = True
except Exception:  # pragma: no cover - depends on optional deps
    _HAVE_HTTP_STACK = False


@unittest.skipUnless(_HAVE_HTTP_STACK, "fastapi + httpx not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["TOKENTRIM_OFFLINE"] = "1"  # force local fakes, no network
        import app.main as main

        fd, cls.log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(cls.log)
        main.gateway.stats_log_file = cls.log  # isolate stats from the real log
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.log):
            os.remove(cls.log)

    def test_chat_generates_then_caches(self):
        first = self.client.post("/chat", json={"query": "when do you open on sunday"})
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["cached"])

        second = self.client.post("/chat", json={"query": "when do you open on sunday"})
        self.assertTrue(second.json()["cached"])

    def test_stats_endpoint(self):
        res = self.client.get("/stats")
        self.assertEqual(res.status_code, 200)
        self.assertIn("total_requests", res.json())

    def test_dashboard_served(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("TokenTrim", res.text)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(_HAVE_HTTP_STACK, "fastapi + httpx not installed")
class ApiExtendedTests(unittest.TestCase):
    """Extended HTTP-level tests covering history, RAG, forced_tier, skip_cache, and stats."""

    @classmethod
    def setUpClass(cls):
        os.environ["TOKENTRIM_OFFLINE"] = "1"
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

    def test_chat_with_history(self):
        history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        res = self.client.post("/chat", json={"query": "how are you", "history": history})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("response", data)
        self.assertFalse(data["cached"])

    def test_chat_with_rag_chunks(self):
        chunks = ["the sky is blue", "the grass is green"]
        res = self.client.post("/chat", json={
            "query": "what colour is the sky",
            "rag_chunks": chunks,
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("naive_cost_usd", data)
        self.assertIn("cost_usd", data)

    def test_skip_cache_over_http(self):
        # Warm the cache
        self.client.post("/chat", json={"query": "unique query skip test"})
        # skip_cache should force a fresh generation
        res = self.client.post("/chat", json={"query": "unique query skip test", "skip_cache": True})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["cached"])

    def test_forced_tier_reflected_in_model_used(self):
        from app import config
        res = self.client.post("/chat", json={
            "query": "simple hello",
            "forced_tier": config.MODEL_MAX,
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["model_used"], config.MODEL_MAX)

    def test_stats_reflects_request_count(self):
        before = self.client.get("/stats").json().get("total_requests", 0)
        self.client.post("/chat", json={"query": "a unique query for stats test 12345"})
        after = self.client.get("/stats").json().get("total_requests", 0)
        self.assertGreater(after, before)

    def test_naive_prompt_and_trimmed_prompt_shape(self):
        res = self.client.post("/chat", json={"query": "what is 2 plus 2"})
        data = res.json()
        self.assertIn("naive_prompt", data)
        self.assertIn("trimmed_prompt", data)
        for msg in data["trimmed_prompt"]:
            self.assertIn("role", msg)
            self.assertIn("content", msg)

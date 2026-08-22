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

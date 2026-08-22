import os
import tempfile
import unittest

from app import stats


class StatsTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)  # start from a non-existent file
        self.addCleanup(lambda: os.path.exists(self.path) and os.remove(self.path))

    def test_missing_file_is_empty_summary(self):
        summary = stats.get_summary(self.path)
        self.assertEqual(summary["total_requests"], 0)
        self.assertEqual(summary["estimated_savings_pct"], 0.0)

    def test_aggregates_cost_and_savings(self):
        # one generated request: cost 0.00043, naive baseline 0.00364
        stats.log_request(
            log_file=self.path,
            cache_hit=False,
            model="qwen3.5-flash",
            input_tokens=3100,
            output_tokens=300,
            cost=0.00043,
            naive_cost=0.00364,
        )
        summary = stats.get_summary(self.path)
        self.assertEqual(summary["total_requests"], 1)
        self.assertEqual(summary["cache_hits"], 0)
        self.assertAlmostEqual(summary["total_cost_usd"], 0.00043, places=6)
        self.assertAlmostEqual(summary["estimated_naive_cost_usd"], 0.00364, places=6)
        self.assertGreater(summary["estimated_savings_pct"], 80.0)

    def test_cache_hit_counts_and_rate(self):
        stats.log_request(log_file=self.path, cache_hit=False, cost=0.001, naive_cost=0.004,
                          input_tokens=100, output_tokens=50)
        stats.log_request(log_file=self.path, cache_hit=True, cost=0.0, naive_cost=0.004,
                          input_tokens=0, output_tokens=0)
        summary = stats.get_summary(self.path)
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["cache_hits"], 1)
        self.assertAlmostEqual(summary["cache_hit_rate"], 0.5)

    def test_fallback_naive_cost_when_not_logged(self):
        # No naive_cost field -> estimated from tokens, must be > 0.
        stats.log_request(log_file=self.path, cache_hit=False, model="qwen-plus",
                          input_tokens=1000, output_tokens=200, cost=0.00064)
        summary = stats.get_summary(self.path)
        self.assertGreater(summary["estimated_naive_cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()

"""Reconcile the build guide's headline worked example against the pricing in
config. If a judge pulls up Alibaba's pricing page, these are the numbers that
must match — so they are pinned in a test.
"""
import unittest

from app import config
from app.router import estimate_cost


class WorkedExampleTests(unittest.TestCase):
    def setUp(self):
        # Before: full prompt, defaulting to qwen-plus. After: compressed +
        # routed to qwen3.5-flash.
        self.before = estimate_cost(config.MODEL_PLUS, 8200, 300)
        self.after = estimate_cost(config.MODEL_FLASH, 3100, 300)

    def test_before_cost_per_call(self):
        self.assertAlmostEqual(self.before, 0.00364, places=5)

    def test_after_cost_per_call(self):
        self.assertAlmostEqual(self.after, 0.00043, places=5)

    def test_reduction_is_88_percent(self):
        pct = (1 - self.after / self.before) * 100
        self.assertAlmostEqual(pct, 88.2, places=1)

    def test_monthly_cost_at_50k_per_day(self):
        requests = 50_000 * 30
        self.assertAlmostEqual(self.before * requests, 5460, delta=1)
        self.assertAlmostEqual(self.after * requests, 645, delta=1)


if __name__ == "__main__":
    unittest.main()

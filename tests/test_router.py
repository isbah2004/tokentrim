import unittest

from app import config
from app.router import (
    estimate_cost,
    naive_cost,
    pick_model,
    score_difficulty,
)


class ScoreDifficultyTests(unittest.TestCase):
    def test_bounds(self):
        self.assertGreaterEqual(score_difficulty("", 0, 0), 0.0)
        self.assertLessEqual(score_difficulty("word " * 100, 20, 50), 1.0)

    def test_trivial_query_is_low(self):
        self.assertLess(score_difficulty("hi", 0, 0), config.ROUTER_SIMPLE_MAX)

    def test_hard_signal_raises_score(self):
        base = score_difficulty("tell me about dogs", 0, 0)
        harder = score_difficulty("analyze and compare these dogs", 0, 0)
        self.assertGreater(harder, base)

    def test_more_context_raises_score(self):
        self.assertGreater(
            score_difficulty("same query", 5, 0),
            score_difficulty("same query", 0, 0),
        )


class PickModelTests(unittest.TestCase):
    def test_simple_query_routes_to_flash(self):
        self.assertEqual(pick_model("hi", 0, 0).model, config.MODEL_FLASH)

    def test_medium_query_routes_to_plus(self):
        # ~30 words, 3 chunks, no hard signal -> ~0.48 -> plus
        query = " ".join(["word"] * 30)
        decision = pick_model(query, 3, 0)
        self.assertEqual(decision.model, config.MODEL_PLUS)

    def test_complex_query_routes_to_max(self):
        # long + max context + hard signal -> 1.0 -> max
        query = "please analyze " + " ".join(["word"] * 50)
        decision = pick_model(query, 5, 10)
        self.assertEqual(decision.model, config.MODEL_MAX)

    def test_decision_reports_difficulty_and_reason(self):
        decision = pick_model("hi", 0, 0)
        self.assertIsInstance(decision.difficulty, float)
        self.assertIn("difficulty=", decision.reason)


class CostTests(unittest.TestCase):
    def test_estimate_cost_matches_manual(self):
        # flash: (1000*0.10 + 500*0.40) / 1e6
        expected = (1000 * 0.10 + 500 * 0.40) / 1_000_000
        self.assertAlmostEqual(estimate_cost(config.MODEL_FLASH, 1000, 500), expected)

    def test_worked_example_reconciles(self):
        # Build guide: after = qwen3.5-flash, 3100 in / 300 out = $0.00043
        after = estimate_cost(config.MODEL_FLASH, 3100, 300)
        self.assertAlmostEqual(after, 0.00043, places=6)

    def test_naive_cost_uses_explicit_uncompressed(self):
        # (8200*2.50 + 300*7.50)/1e6 on the flagship
        expected = (8200 * 2.50 + 300 * 7.50) / 1_000_000
        got = naive_cost(input_tokens=3100, output_tokens=300, uncompressed_input_tokens=8200)
        self.assertAlmostEqual(got, expected)

    def test_naive_cost_exceeds_optimized_cost(self):
        optimized = estimate_cost(config.MODEL_FLASH, 3100, 300)
        baseline = naive_cost(input_tokens=3100, output_tokens=300)
        self.assertGreater(baseline, optimized)


if __name__ == "__main__":
    unittest.main()

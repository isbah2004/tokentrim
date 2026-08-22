import unittest

from app import config


class ConfigTests(unittest.TestCase):
    def test_validate_passes_with_defaults(self):
        self.assertEqual(config.validate(), [])

    def test_pricing_covers_all_tiers(self):
        for tier in (config.MODEL_FLASH, config.MODEL_PLUS, config.MODEL_MAX):
            self.assertIn(tier, config.PRICING)
            self.assertIn("input", config.PRICING[tier])
            self.assertIn("output", config.PRICING[tier])

    def test_pricing_tiers_are_ordered_cheap_to_flagship(self):
        flash = config.PRICING[config.MODEL_FLASH]
        plus = config.PRICING[config.MODEL_PLUS]
        mx = config.PRICING[config.MODEL_MAX]
        self.assertLess(flash["input"], plus["input"])
        self.assertLess(plus["input"], mx["input"])
        self.assertLess(flash["output"], plus["output"])
        self.assertLess(plus["output"], mx["output"])

    def test_router_thresholds_ordered(self):
        self.assertTrue(0 < config.ROUTER_SIMPLE_MAX < config.ROUTER_MEDIUM_MAX < 1)

    def test_embed_dim_positive(self):
        self.assertGreater(config.EMBED_DIM, 0)


if __name__ == "__main__":
    unittest.main()

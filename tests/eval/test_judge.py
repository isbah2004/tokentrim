"""Unit tests for the LLM-as-judge module."""
import unittest
from unittest.mock import MagicMock

from tests.eval.judge import JudgeScore, LLMJudge, RuleBasedJudge, make_judge


class RuleBasedJudgeTests(unittest.TestCase):
    def setUp(self):
        self.judge = RuleBasedJudge()

    def test_exact_match_correctness_one(self):
        score = self.judge.score("q", "The answer is 42.", "The answer is 42.")
        self.assertAlmostEqual(score.correctness, 1.0)

    def test_partial_match_correctness_one(self):
        """Golden substring anywhere in response counts as correct."""
        score = self.judge.score("q", "Paris", "The capital of France is Paris.")
        self.assertAlmostEqual(score.correctness, 1.0)

    def test_missing_answer_correctness_zero(self):
        score = self.judge.score("q", "Paris", "I'm not sure about that.")
        self.assertAlmostEqual(score.correctness, 0.0)

    def test_case_insensitive(self):
        score = self.judge.score("q", "paris", "The city is PARIS.")
        self.assertAlmostEqual(score.correctness, 1.0)

    def test_overall_between_zero_and_one(self):
        score = self.judge.score("what?", "something", "completely different")
        self.assertGreaterEqual(score.overall, 0.0)
        self.assertLessEqual(score.overall, 1.0)

    def test_good_response_high_overall(self):
        golden = "Paris."
        response = "The capital of France is Paris."
        score = self.judge.score("capital of france?", golden, response)
        self.assertGreater(score.overall, 0.5)

    def test_verbose_response_lower_conciseness(self):
        golden = "Yes."
        verbose = "Yes " * 100  # extremely verbose
        score = self.judge.score("q", golden, verbose)
        self.assertLess(score.conciseness, 1.0)

    def test_concise_response_full_conciseness(self):
        golden = "The answer is 42."
        response = "42"
        score = self.judge.score("q", golden, response)
        self.assertAlmostEqual(score.conciseness, 1.0)

    def test_returns_judge_score_instance(self):
        score = self.judge.score("q", "g", "r")
        self.assertIsInstance(score, JudgeScore)

    def test_explanation_is_string(self):
        score = self.judge.score("q", "golden", "response")
        self.assertIsInstance(score.explanation, str)
        self.assertGreater(len(score.explanation), 0)


class LLMJudgeParsingTests(unittest.TestCase):
    """Tests for LLMJudge._parse_response — no actual API calls."""

    def setUp(self):
        self.judge = LLMJudge(client=MagicMock(), model="qwen-plus")

    def test_parse_clean_json(self):
        raw = '{"correctness": 5, "completeness": 4, "conciseness": 3, "hallucination_free": 5, "explanation": "Good answer."}'
        score = self.judge._parse_response(raw)
        self.assertAlmostEqual(score.correctness, 1.0)  # (5-1)/4 = 1.0
        self.assertAlmostEqual(score.completeness, 0.75)  # (4-1)/4 = 0.75
        self.assertEqual(score.explanation, "Good answer.")

    def test_parse_fenced_json(self):
        raw = '```json\n{"correctness": 3, "completeness": 3, "conciseness": 3, "hallucination_free": 3, "explanation": "ok"}\n```'
        score = self.judge._parse_response(raw)
        self.assertAlmostEqual(score.correctness, 0.5)  # (3-1)/4 = 0.5
        self.assertAlmostEqual(score.overall, 0.5)

    def test_parse_fenced_no_language(self):
        raw = '```\n{"correctness": 5, "completeness": 5, "conciseness": 5, "hallucination_free": 5, "explanation": "perfect"}\n```'
        score = self.judge._parse_response(raw)
        self.assertAlmostEqual(score.correctness, 1.0)

    def test_regex_fallback(self):
        # Malformed JSON but values extractable by regex
        raw = 'correctness: 4, completeness: 3, conciseness: 5, hallucination_free: 4, explanation: "ok"'
        score = self.judge._parse_response(raw)
        # At minimum correctness should parse
        self.assertGreaterEqual(score.overall, 0.0)
        self.assertLessEqual(score.overall, 1.0)

    def test_prompt_contains_rubric(self):
        """Verify that the RUBRIC constant includes expected rubric keywords."""
        rubric = LLMJudge.RUBRIC
        self.assertIn("correctness", rubric)
        self.assertIn("completeness", rubric)
        self.assertIn("conciseness", rubric)
        self.assertIn("hallucination_free", rubric)
        self.assertIn("1", rubric)
        self.assertIn("5", rubric)


class MakeJudgeFactoryTests(unittest.TestCase):
    def test_default_is_rule_based(self):
        import os
        os.environ.pop("TOKENTRIM_JUDGE_LIVE", None)
        judge = make_judge()
        self.assertIsInstance(judge, RuleBasedJudge)

    def test_rule_based_when_live_not_set(self):
        import os
        os.environ["TOKENTRIM_JUDGE_LIVE"] = "0"
        judge = make_judge()
        self.assertIsInstance(judge, RuleBasedJudge)
        os.environ.pop("TOKENTRIM_JUDGE_LIVE", None)


if __name__ == "__main__":
    unittest.main()

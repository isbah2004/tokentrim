"""Component tests for app.vectormath — cosine_similarity, dot, norm."""
import math
import unittest

from app.vectormath import cosine_similarity, dot, norm


class DotProductTests(unittest.TestCase):
    def test_basic_dot(self):
        self.assertAlmostEqual(dot([1, 2, 3], [4, 5, 6]), 32.0)

    def test_zero_vector(self):
        self.assertEqual(dot([0, 0, 0], [1, 2, 3]), 0.0)

    def test_orthogonal(self):
        self.assertEqual(dot([1, 0], [0, 1]), 0.0)


class NormTests(unittest.TestCase):
    def test_unit_vector(self):
        self.assertAlmostEqual(norm([1, 0, 0]), 1.0)

    def test_zero_vector(self):
        self.assertAlmostEqual(norm([0, 0, 0]), 0.0)

    def test_known_norm(self):
        self.assertAlmostEqual(norm([3, 4]), 5.0)


class CosineSimilarityTests(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        v = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=9)

    def test_opposite_vectors_score_minus_one(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(a, b), -1.0, places=9)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0, places=9)

    def test_zero_vector_returns_zero(self):
        self.assertEqual(cosine_similarity([0, 0], [1, 1]), 0.0)

    def test_both_zero_vectors_returns_zero(self):
        self.assertEqual(cosine_similarity([0, 0], [0, 0]), 0.0)

    def test_normalised_vectors_are_dot_product(self):
        a = [3.0, 4.0]
        na = norm(a)
        a_unit = [x / na for x in a]
        b = [4.0, 3.0]
        nb = norm(b)
        b_unit = [x / nb for x in b]
        expected = dot(a_unit, b_unit)
        self.assertAlmostEqual(cosine_similarity(a, b), expected, places=9)

    def test_result_in_minus_one_to_one(self):
        import random
        random.seed(42)
        for _ in range(20):
            a = [random.uniform(-5, 5) for _ in range(10)]
            b = [random.uniform(-5, 5) for _ in range(10)]
            sim = cosine_similarity(a, b)
            self.assertGreaterEqual(sim, -1.0 - 1e-9)
            self.assertLessEqual(sim, 1.0 + 1e-9)


if __name__ == "__main__":
    unittest.main()

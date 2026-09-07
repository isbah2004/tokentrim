import unittest

from app.embeddings import HashingEmbeddingProvider
from app.vectormath import cosine_similarity, norm


class HashingEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.embedder = HashingEmbeddingProvider(dim=256)

    def test_dimension(self):
        self.assertEqual(len(self.embedder.embed("hello world")), 256)

    def test_deterministic(self):
        a = self.embedder.embed("the quick brown fox")
        b = self.embedder.embed("the quick brown fox")
        self.assertEqual(a, b)

    def test_identical_text_cosine_is_one(self):
        a = self.embedder.embed("what are your opening hours")
        b = self.embedder.embed("what are your opening hours")
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0, places=6)

    def test_nonempty_vector_is_unit_length(self):
        self.assertAlmostEqual(norm(self.embedder.embed("some text here")), 1.0, places=6)

    def test_overlapping_more_similar_than_disjoint(self):
        base = self.embedder.embed("annual revenue report figures")
        overlap = self.embedder.embed("annual revenue report summary")
        disjoint = self.embedder.embed("weather forecast tomorrow morning")
        self.assertGreater(
            cosine_similarity(base, overlap),
            cosine_similarity(base, disjoint),
        )

    def test_empty_text_is_zero_vector(self):
        vec = self.embedder.embed("")
        self.assertEqual(set(vec), {0.0})
        # cosine against anything is defined as 0, not a division error
        self.assertEqual(cosine_similarity(vec, self.embedder.embed("hello")), 0.0)

    def test_batch_matches_single(self):
        texts = ["one two", "three four"]
        batch = self.embedder.embed_batch(texts)
        self.assertEqual(batch[0], self.embedder.embed("one two"))
        self.assertEqual(batch[1], self.embedder.embed("three four"))


if __name__ == "__main__":
    unittest.main()


class HashingEmbedderDeterminismTests(unittest.TestCase):
    """Hashing embedder must be deterministic across different instances."""

    def test_deterministic_across_instances(self):
        """Two separately-constructed embedders must produce identical vectors."""
        e1 = HashingEmbeddingProvider(dim=128)
        e2 = HashingEmbeddingProvider(dim=128)
        text = "process restarts cannot change the embedding"
        self.assertEqual(e1.embed(text), e2.embed(text))

    def test_different_dims_different_lengths(self):
        e64 = HashingEmbeddingProvider(dim=64)
        e512 = HashingEmbeddingProvider(dim=512)
        self.assertEqual(len(e64.embed("hello")), 64)
        self.assertEqual(len(e512.embed("hello")), 512)

    def test_all_numeric_floats(self):
        embedder = HashingEmbeddingProvider(dim=64)
        vec = embedder.embed("test text here")
        for v in vec:
            self.assertIsInstance(v, float)

    def test_batch_size_matches_input_count(self):
        embedder = HashingEmbeddingProvider(dim=64)
        texts = ["a", "bb", "ccc", "dddd"]
        result = embedder.embed_batch(texts)
        self.assertEqual(len(result), 4)
        for v in result:
            self.assertEqual(len(v), 64)

import unittest

from app.cache import InMemoryVectorStore, SemanticCache


class FakeEmbedder:
    """Maps known strings to fixed vectors so threshold behaviour is exact and
    independent of any real embedding model."""

    def __init__(self, mapping):
        self.mapping = mapping

    def embed(self, text):
        return self.mapping[text]

    def embed_batch(self, texts):
        return [self.mapping[t] for t in texts]


# cosine([1,0], v):  dup=1.00, close=0.96, far=0.00
VECTORS = {
    "q": [1.0, 0.0],
    "q_dup": [1.0, 0.0],
    "q_close": [0.96, 0.28],
    "q_far": [0.0, 1.0],
}


class InMemoryVectorStoreTests(unittest.TestCase):
    def test_empty_store_returns_none(self):
        self.assertIsNone(InMemoryVectorStore().nearest([1.0, 0.0]))

    def test_returns_closest_entry(self):
        store = InMemoryVectorStore()
        store.add("q", "answer-q", [1.0, 0.0])
        store.add("q_far", "answer-far", [0.0, 1.0])
        entry, sim = store.nearest([0.9, 0.1])
        self.assertEqual(entry.query, "q")
        self.assertGreater(sim, 0.9)


class SemanticCacheTests(unittest.TestCase):
    def _cache(self, threshold):
        return SemanticCache(
            store=InMemoryVectorStore(),
            embedder=FakeEmbedder(VECTORS),
            similarity_threshold=threshold,
        )

    def test_lookup_on_empty_cache_is_miss(self):
        self.assertIsNone(self._cache(0.92).lookup("q"))

    def test_exact_duplicate_hits(self):
        cache = self._cache(0.92)
        cache.store_answer("q", "the answer")
        hit = cache.lookup("q_dup")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.response, "the answer")
        self.assertAlmostEqual(hit.similarity, 1.0, places=6)
        self.assertEqual(hit.original_query, "q")

    def test_near_duplicate_above_threshold_hits(self):
        cache = self._cache(0.92)
        cache.store_answer("q", "the answer")
        hit = cache.lookup("q_close")  # similarity 0.96 >= 0.92
        self.assertIsNotNone(hit)
        self.assertEqual(hit.response, "the answer")

    def test_near_duplicate_below_threshold_misses(self):
        cache = self._cache(0.98)  # raise the bar above 0.96
        cache.store_answer("q", "the answer")
        self.assertIsNone(cache.lookup("q_close"))

    def test_unrelated_query_misses(self):
        cache = self._cache(0.92)
        cache.store_answer("q", "the answer")
        self.assertIsNone(cache.lookup("q_far"))


if __name__ == "__main__":
    unittest.main()

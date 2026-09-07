import unittest

from app.compressor import Message, build_prompt, compress_history, rerank_chunks


class CompressHistoryTests(unittest.TestCase):
    def test_short_history_untouched(self):
        history = [Message("user", "hi"), Message("assistant", "hello")]
        self.assertEqual(compress_history(history, keep_verbatim=2), history)

    def test_older_turns_folded_into_summary(self):
        history = [
            Message("user", "first"),
            Message("assistant", "second"),
            Message("user", "third"),
            Message("assistant", "fourth"),
        ]
        out = compress_history(history, keep_verbatim=2)
        self.assertEqual(len(out), 3)  # 1 summary + 2 verbatim
        self.assertEqual(out[0].role, "system")
        self.assertIn("first", out[0].content)
        self.assertIn("second", out[0].content)
        self.assertEqual(out[1:], history[-2:])

    def test_summary_truncation_adds_ellipsis(self):
        history = [Message("user", "x" * 1000), Message("user", "a"), Message("user", "b")]
        out = compress_history(history, keep_verbatim=2, max_summary_chars=50)
        self.assertTrue(out[0].content.endswith("..."))

    def test_keep_verbatim_zero_folds_everything(self):
        history = [Message("user", "a"), Message("user", "b")]
        out = compress_history(history, keep_verbatim=0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].role, "system")


class RerankChunksTests(unittest.TestCase):
    def setUp(self):
        # 2D embeddings; query points along x-axis
        self.query = [1.0, 0.0]
        self.chunks = [
            ("aligned", [1.0, 0.0]),      # sim 1.0
            ("orthogonal", [0.0, 1.0]),   # sim 0.0
            ("mostly", [0.9, 0.2]),       # sim ~0.98
        ]

    def test_top_k_ordering(self):
        out = rerank_chunks(self.query, self.chunks, top_k=2)
        self.assertEqual(out, ["aligned", "mostly"])

    def test_top_k_respected(self):
        self.assertEqual(len(rerank_chunks(self.query, self.chunks, top_k=1)), 1)

    def test_top_k_zero_returns_empty(self):
        self.assertEqual(rerank_chunks(self.query, self.chunks, top_k=0), [])


class BuildPromptTests(unittest.TestCase):
    def test_structure_system_first_query_last(self):
        msgs = build_prompt(
            system_prompt="You are helpful.",
            compressed_history=[Message("user", "earlier")],
            rag_chunks=["chunk A", "chunk B"],
            query="the question",
        )
        self.assertEqual(msgs[0]["role"], "system")
        self.assertIn("You are helpful.", msgs[0]["content"])
        self.assertIn("chunk A", msgs[0]["content"])
        self.assertIn("Context:", msgs[0]["content"])
        self.assertEqual(msgs[-1], {"role": "user", "content": "the question"})
        self.assertEqual(msgs[1], {"role": "user", "content": "earlier"})

    def test_no_context_header_when_no_chunks(self):
        msgs = build_prompt("sys", [], [], "q")
        self.assertNotIn("Context:", msgs[0]["content"])
        self.assertEqual(msgs[0]["content"], "sys")


if __name__ == "__main__":
    unittest.main()


class CompressionTokenReductionTests(unittest.TestCase):
    """Compression must reduce history tokens; query is last message in build_prompt."""

    def test_compression_reduces_history_tokens(self):
        from app.tokens import estimate_message_tokens
        history = [
            Message("user", "word " * 100),
            Message("assistant", "word " * 100),
            Message("user", "word " * 100),
            Message("assistant", "word " * 100),
            Message("user", "word " * 100),
            Message("assistant", "word " * 100),
        ]
        compressed = compress_history(history, keep_verbatim=2)
        orig_tokens = estimate_message_tokens(
            [{"role": m.role, "content": m.content} for m in history]
        )
        comp_tokens = estimate_message_tokens(
            [{"role": m.role, "content": m.content} for m in compressed]
        )
        self.assertLess(comp_tokens, orig_tokens,
                        "Compressed history should have fewer tokens than original")

    def test_rerank_order_with_hashing_embedder(self):
        """Reranking with HashingEmbeddingProvider should prefer text-similar chunks."""
        from app.embeddings import HashingEmbeddingProvider
        embedder = HashingEmbeddingProvider(dim=256)
        query = "annual revenue report"
        q_emb = embedder.embed(query)
        chunks = [
            ("unrelated weather forecast tomorrow", embedder.embed("unrelated weather forecast tomorrow")),
            ("annual revenue report figures Q4", embedder.embed("annual revenue report figures Q4")),
            ("completely different topic", embedder.embed("completely different topic")),
        ]
        result = rerank_chunks(q_emb, chunks, top_k=1)
        self.assertEqual(result[0], "annual revenue report figures Q4")

    def test_query_is_last_message_in_build_prompt(self):
        msgs = build_prompt(
            system_prompt="sys",
            compressed_history=[Message("user", "earlier")],
            rag_chunks=[],
            query="the final user question",
        )
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertEqual(msgs[-1]["content"], "the final user question")

    def test_negative_keep_verbatim_raises(self):
        with self.assertRaises(ValueError):
            compress_history([Message("user", "hi")], keep_verbatim=-1)

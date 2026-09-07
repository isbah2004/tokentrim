"""Component tests for app.tokens — estimate_tokens and estimate_message_tokens."""
import unittest

from app.tokens import estimate_message_tokens, estimate_tokens


class EstimateTokensTests(unittest.TestCase):
    def test_empty_string_returns_one(self):
        # max(1, ...) floor ensures even empty strings count as at least 1 token
        self.assertEqual(estimate_tokens(""), 1)

    def test_single_word(self):
        # 1 word * 1.3 = 1.3, rounded to 1
        self.assertGreaterEqual(estimate_tokens("hello"), 1)

    def test_proportional_to_length(self):
        short = estimate_tokens("short")
        long = estimate_tokens("this is a much longer sentence with many words in it")
        self.assertGreater(long, short)

    def test_many_words(self):
        # 10 words → 13 tokens (rounded)
        text = " ".join(["word"] * 10)
        result = estimate_tokens(text)
        self.assertEqual(result, round(10 * 1.3))

    def test_whitespace_only_returns_one(self):
        self.assertEqual(estimate_tokens("   "), 1)

    def test_unicode_text(self):
        # Should not raise; multi-byte chars treated as words by split()
        result = estimate_tokens("مرحبا بالعالم")
        self.assertGreaterEqual(result, 1)

    def test_newlines_treated_as_whitespace(self):
        text = "line one\nline two\nline three"
        result = estimate_tokens(text)
        # 5 words → 7 tokens (rounded)
        self.assertGreater(result, 1)

    def test_returns_int(self):
        self.assertIsInstance(estimate_tokens("some text"), int)


class EstimateMessageTokensTests(unittest.TestCase):
    def test_empty_list_is_zero(self):
        self.assertEqual(estimate_message_tokens([]), 0)

    def test_single_message(self):
        msgs = [{"role": "user", "content": "hello world"}]
        result = estimate_message_tokens(msgs)
        self.assertEqual(result, estimate_tokens("hello world"))

    def test_multiple_messages_summed(self):
        msgs = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "second message here"},
        ]
        expected = estimate_tokens("first message") + estimate_tokens("second message here")
        self.assertEqual(estimate_message_tokens(msgs), expected)

    def test_missing_content_key_counts_as_empty(self):
        msgs = [{"role": "user"}]  # no "content" key
        result = estimate_message_tokens(msgs)
        self.assertEqual(result, estimate_tokens(""))

    def test_system_message_counted(self):
        msgs = [
            {"role": "system", "content": "You are a helpful assistant with many capabilities."},
            {"role": "user", "content": "hi"},
        ]
        total = estimate_message_tokens(msgs)
        self.assertGreater(total, estimate_tokens("hi"))


if __name__ == "__main__":
    unittest.main()

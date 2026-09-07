"""Component tests for the qwen_client module.

Tests FakeChatModel behaviour and QwenChatModel usage-parsing with a mocked
completion object — no network calls in this file.
"""
import unittest
from unittest.mock import MagicMock, patch

from app.qwen_client import ChatResult, FakeChatModel, QwenChatModel
from app.tokens import estimate_message_tokens, estimate_tokens


class FakeChatModelTests(unittest.TestCase):
    def test_fixed_answer_returned(self):
        model = FakeChatModel(answer="hello there")
        result = model.generate("qwen-flash", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.text, "hello there")

    def test_default_answer_contains_model_name(self):
        model = FakeChatModel()
        result = model.generate("qwen-plus", [{"role": "user", "content": "q"}])
        self.assertIn("qwen-plus", result.text)

    def test_prompt_tokens_match_message_estimate(self):
        msgs = [{"role": "user", "content": "what are the store hours on sunday"}]
        model = FakeChatModel(answer="We are open 9-5.")
        result = model.generate("qwen-flash", msgs)
        self.assertEqual(result.prompt_tokens, estimate_message_tokens(msgs))

    def test_completion_tokens_match_answer_estimate(self):
        answer = "This is a multi word answer for testing purposes."
        model = FakeChatModel(answer=answer)
        result = model.generate("qwen-flash", [{"role": "user", "content": "q"}])
        self.assertEqual(result.completion_tokens, estimate_tokens(answer))

    def test_cached_tokens_always_zero(self):
        model = FakeChatModel(answer="ok")
        result = model.generate("qwen-flash", [{"role": "user", "content": "q"}])
        self.assertEqual(result.cached_tokens, 0)

    def test_model_field_set_correctly(self):
        model = FakeChatModel(answer="ok")
        result = model.generate("qwen3.7-max", [{"role": "user", "content": "q"}])
        self.assertEqual(result.model, "qwen3.7-max")

    def test_none_answer_uses_default(self):
        model = FakeChatModel(answer=None)
        result = model.generate("qwen-plus", [{"role": "user", "content": "q"}])
        self.assertIsInstance(result.text, str)
        self.assertGreater(len(result.text), 0)


class QwenChatModelUsageParsingTests(unittest.TestCase):
    """Tests for QwenChatModel.generate() usage extraction — mocked completions."""

    def _make_completion(self, prompt_tokens=100, completion_tokens=50,
                         cached_tokens=None, cached_via_details=None):
        """Build a mock completion object matching the OpenAI API shape."""
        usage = MagicMock()
        usage.prompt_tokens = prompt_tokens
        usage.completion_tokens = completion_tokens

        if cached_tokens is not None:
            usage.cached_tokens = cached_tokens
        else:
            del usage.cached_tokens  # simulate AttributeError path

        if cached_via_details is not None:
            details = MagicMock()
            details.cached_tokens = cached_via_details
            usage.prompt_tokens_details = details
        else:
            usage.prompt_tokens_details = None

        completion = MagicMock()
        completion.usage = usage
        completion.choices = [MagicMock()]
        completion.choices[0].message.content = "generated text"
        return completion

    def _model_with_mock(self, completion):
        m = QwenChatModel(client=MagicMock())
        m._get_client().chat.completions.create.return_value = completion
        return m

    def test_basic_token_counts(self):
        comp = self._make_completion(prompt_tokens=200, completion_tokens=30)
        model = self._model_with_mock(comp)
        result = model.generate("qwen-plus", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.prompt_tokens, 200)
        self.assertEqual(result.completion_tokens, 30)
        self.assertEqual(result.text, "generated text")

    def test_cached_tokens_from_top_level(self):
        comp = self._make_completion(prompt_tokens=100, completion_tokens=20, cached_tokens=40)
        model = self._model_with_mock(comp)
        result = model.generate("qwen-plus", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.cached_tokens, 40)

    def test_cached_tokens_fallback_to_details(self):
        """cached_tokens not on usage but present on prompt_tokens_details."""
        comp = self._make_completion(prompt_tokens=100, completion_tokens=20,
                                     cached_via_details=60)
        model = self._model_with_mock(comp)
        result = model.generate("qwen-plus", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.cached_tokens, 60)

    def test_no_cached_tokens_defaults_to_zero(self):
        comp = self._make_completion(prompt_tokens=100, completion_tokens=20)
        model = self._model_with_mock(comp)
        result = model.generate("qwen-plus", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.cached_tokens, 0)

    def test_result_is_chat_result_instance(self):
        comp = self._make_completion()
        model = self._model_with_mock(comp)
        result = model.generate("qwen-flash", [{"role": "user", "content": "q"}])
        self.assertIsInstance(result, ChatResult)


if __name__ == "__main__":
    unittest.main()

"""Chat model wrapper.

One tiny interface, ``ChatModel.generate(model, messages) -> ChatResult``, with
two implementations:

- ``QwenChatModel`` — the production path via the OpenAI-compatible client,
  returning the model's real token ``usage`` (including implicit-cache hits when
  the API reports them). Imports ``openai`` lazily.
- ``FakeChatModel`` — an offline, deterministic model so the gateway and its
  end-to-end tests run with no network. Token counts come from ``app.tokens``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, runtime_checkable

from app import config
from app.tokens import estimate_message_tokens, estimate_tokens


@dataclass
class ChatResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    model: str = ""


@runtime_checkable
class ChatModel(Protocol):
    def generate(self, model: str, messages: List[Dict[str, str]]) -> ChatResult:
        ...


class QwenChatModel:
    def __init__(self, client=None):
        self._client = client

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy

            self._client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.BASE_URL)
        return self._client

    def generate(self, model: str, messages: List[Dict[str, str]]) -> ChatResult:
        completion = self._get_client().chat.completions.create(model=model, messages=messages)
        usage = completion.usage
        # cached_tokens is exposed differently across API versions; check both.
        cached = getattr(usage, "cached_tokens", 0) or 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", cached) or cached
        return ChatResult(
            text=completion.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cached_tokens=cached,
            model=model,
        )


class FakeChatModel:
    """Deterministic offline model. Returns a canned answer and derives token
    counts from the prompt/answer text so cost math is exercised realistically."""

    def __init__(self, answer: Optional[str] = None):
        self._answer = answer

    def generate(self, model: str, messages: List[Dict[str, str]]) -> ChatResult:
        answer = self._answer if self._answer is not None else f"[offline:{model}] response generated locally."
        return ChatResult(
            text=answer,
            prompt_tokens=estimate_message_tokens(messages),
            completion_tokens=estimate_tokens(answer),
            cached_tokens=0,
            model=model,
        )

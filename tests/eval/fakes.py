"""Offline fakes for the evaluation harness.

MappingFakeChatModel maps exact query text → a pre-configured golden answer,
so the offline RuleBasedJudge receives real signal (the expected string is
present) without any network call.
"""
from __future__ import annotations

from typing import Dict, List

from app.qwen_client import ChatResult
from app.tokens import estimate_message_tokens, estimate_tokens


class MappingFakeChatModel:
    """Maps a query string to a configured answer.

    When the last user message matches a key in ``mapping``, returns the
    configured golden answer. Falls back to a generic offline response so tests
    that don't need exact signal still complete.
    """

    def __init__(self, mapping: Dict[str, str], fallback: str = "[offline] no mapping found."):
        self.mapping = mapping
        self.fallback = fallback

    def generate(self, model: str, messages: List[Dict[str, str]]) -> ChatResult:
        # Find the last user message as the lookup key
        query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                query = m.get("content", "")
                break

        answer = self.mapping.get(query, self.fallback)
        return ChatResult(
            text=answer,
            prompt_tokens=estimate_message_tokens(messages),
            completion_tokens=estimate_tokens(answer),
            cached_tokens=0,
            model=model,
        )

"""Rough, offline token estimation.

The live path uses the model's real ``usage`` counts. These helpers are only
for (a) the offline ``FakeChatModel`` and (b) measuring the compression ratio
that drives the dashboard's uncompressed baseline. They intentionally avoid a
tokenizer dependency; ~1.3 tokens per whitespace word is a serviceable
approximation for English prose.
"""
from __future__ import annotations

from typing import Dict, List

_TOKENS_PER_WORD = 1.3


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return max(1, round(words * _TOKENS_PER_WORD))


def estimate_message_tokens(messages: List[Dict[str, str]]) -> int:
    return sum(estimate_tokens(m.get("content", "")) for m in messages)

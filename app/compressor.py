"""Layer 2 — Context Compressor.

Runs only on a cache miss. Two jobs: trim chat history, and shrink/rerank RAG
context. Both cut input tokens before the request reaches a model, and
``build_prompt`` orders the result so it also qualifies for Model Studio's
automatic prefix-cache discount.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.vectormath import cosine_similarity


@dataclass
class Message:
    role: str
    content: str


def compress_history(
    history: List[Message],
    keep_verbatim: int = 2,
    max_summary_chars: int = 400,
) -> List[Message]:
    """Keep the last ``keep_verbatim`` turns exactly; fold everything older into
    one short summary turn.

    For a hackathon MVP a cheap extractive summary (join + truncate) is enough;
    an LLM-generated summary via the cheap tier is the natural v2 upgrade.
    """
    if keep_verbatim < 0:
        raise ValueError("keep_verbatim must be >= 0")
    if len(history) <= keep_verbatim:
        return list(history)

    older = history[: len(history) - keep_verbatim] if keep_verbatim else history
    recent = history[len(history) - keep_verbatim :] if keep_verbatim else []

    joined = " ".join(m.content for m in older)
    summary = joined[:max_summary_chars]
    if len(joined) > max_summary_chars:
        summary += "..."

    summary_msg = Message(role="system", content=f"Earlier conversation summary: {summary}")
    return [summary_msg] + list(recent)


def rerank_chunks(
    query_embedding: List[float],
    chunks: List[Tuple[str, List[float]]],
    top_k: int = 2,
) -> List[str]:
    """Given (chunk_text, chunk_embedding) pairs computed at index time, keep
    only the ``top_k`` most relevant to *this* query instead of stuffing every
    retrieved chunk into the prompt."""
    if top_k <= 0:
        return []
    scored = [
        (cosine_similarity(query_embedding, emb), text) for text, emb in chunks
    ]
    # stable sort by descending similarity; ties keep original retrieval order
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in scored[:top_k]]


def build_prompt(
    system_prompt: str,
    compressed_history: List[Message],
    rag_chunks: List[str],
    query: str,
) -> List[Dict[str, str]]:
    """Assemble the final message list.

    Stable content (system prompt, then RAG context) goes first and the unique
    per-request content (the question) goes last — that ordering is what makes
    repeated prefixes eligible for Alibaba's automatic implicit-cache discount
    on top of everything TokenTrim does explicitly.
    """
    context_block = "\n\n".join(rag_chunks)
    system_content = system_prompt
    if context_block:
        system_content = f"{system_prompt}\n\nContext:\n{context_block}"

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
    messages += [{"role": m.role, "content": m.content} for m in compressed_history]
    messages.append({"role": "user", "content": query})
    return messages

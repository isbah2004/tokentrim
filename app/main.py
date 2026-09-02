"""FastAPI gateway: /chat, /stats, and the dashboard.

A thin HTTP shell over ``app.pipeline.Gateway``. ``build_gateway()`` wires the
real Qwen + pgvector components when they're available and configured, and
falls back to fully offline components otherwise — so the server (and the
dashboard) runs for a demo even without a key or a database. Force offline with
TOKENTRIM_OFFLINE=1.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import config
from app.cache import InMemoryVectorStore, SemanticCache
from app.embeddings import HashingEmbeddingProvider, QwenEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import FakeChatModel, QwenChatModel
from app.stats import get_summary

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _openai_available() -> bool:
    try:
        import openai  # noqa: F401

        return True
    except ModuleNotFoundError:
        return False


def _make_pg_store():
    """Return a PgVectorStore if psycopg2 + DATABASE_URL are usable, else None."""
    if not config.DATABASE_URL:
        return None
    try:
        import psycopg2

        from app.cache import PgVectorStore

        conn = psycopg2.connect(config.DATABASE_URL)
        return PgVectorStore(conn)
    except Exception as exc:  # pragma: no cover - depends on live infra
        print(f"[tokentrim] Postgres unavailable ({exc}); using in-memory cache.")
        return None


def build_gateway() -> Gateway:
    offline = os.getenv("TOKENTRIM_OFFLINE") == "1"
    live = (not offline) and _openai_available() and bool(config.DASHSCOPE_API_KEY)

    embedder = QwenEmbeddingProvider() if live else HashingEmbeddingProvider()
    chat_model = QwenChatModel() if live else FakeChatModel()
    store = _make_pg_store() or InMemoryVectorStore()

    mode = "LIVE (Qwen)" if live else "OFFLINE (local fakes)"
    store_kind = type(store).__name__
    print(f"[tokentrim] gateway mode: {mode}; vector store: {store_kind}")

    cache = SemanticCache(store=store, embedder=embedder)
    return Gateway(cache=cache, chat_model=chat_model)


app = FastAPI(title="TokenTrim", version="0.1.0")
gateway = build_gateway()


class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = []
    rag_chunks: List[str] = []
    skip_cache: bool = False
    skip_compression: bool = False
    forced_tier: Optional[str] = None


@app.post("/chat")
def chat(req: ChatRequest) -> Dict:
    return gateway.chat(
        query=req.query,
        history=req.history,
        rag_chunks=req.rag_chunks,
        skip_cache=req.skip_cache,
        skip_compression=req.skip_compression,
        forced_tier=req.forced_tier,
    ).as_dict()


@app.get("/stats")
def stats() -> Dict:
    return get_summary(gateway.stats_log_file)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    index = STATIC_DIR / "dashboard.html"
    if not index.exists():
        return "<h1>TokenTrim</h1><p>dashboard.html not found.</p>"
    return index.read_text(encoding="utf-8")


@app.get("/test-chat", response_class=HTMLResponse)
def test_chat() -> str:
    index = STATIC_DIR / "chat.html"
    if not index.exists():
        return "<h1>TokenTrim</h1><p>chat.html not found.</p>"
    return index.read_text(encoding="utf-8")

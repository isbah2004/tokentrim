# 23. Main Techniques We Plan to Use

## The Three Strategies

TokenTrim's architecture is built around three major cost-reduction strategies, each operating at a different point in the pipeline:

```
User Query
      ↓
  [1] RAG Chunk Reranking    ← Reduce irrelevant context before the model sees it
      ↓
  [2] History Trimming       ← Compress old conversation turns
      ↓
  [3] Model Routing          ← Use the cheapest model that can handle the query
      ↓
  Qwen API Call (minimized cost)
```

## 1. RAG Chunk Reranking

### What It Does

When a RAG system retrieves chunks from a knowledge base, it typically returns **more chunks than necessary**. The retriever casts a wide net to avoid missing relevant information, but many retrieved chunks are only marginally relevant.

[`rerank_chunks()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L50-L65) takes the retrieved chunks and keeps only the `top_k` most relevant ones based on cosine similarity to the current query.

### Cost Savings

| Scenario | Without Reranking | With Reranking (top_k=2) |
|----------|------------------|--------------------------|
| Retrieved chunks | 5 chunks × 500 tokens = 2,500 tokens | 2 chunks × 500 tokens = 1,000 tokens |
| Token savings | — | 1,500 tokens saved |
| At Flash pricing ($0.10/1M) | $0.000250 | $0.000100 |
| At Max pricing ($2.50/1M) | $0.006250 | $0.002500 |

**Savings per request**: ~60% of RAG context tokens.

### Exact Strategy

```python
def rerank_chunks(query_embedding, chunks, top_k=2):
    scored = [(cosine_similarity(query_embedding, emb), text) for text, emb in chunks]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in scored[:top_k]]
```

- Score each chunk by its cosine similarity to the query embedding.
- Keep only the top 2 (configurable).
- Discard the rest.

## 2. History Trimming

### What It Does

In multi-turn conversations, the full history is sent as context. A 20-turn conversation might include 8,000+ tokens of history, most of which is irrelevant to the current question.

[`compress_history()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L22-L47) keeps the **last 2 turns verbatim** and folds everything older into a single short summary.

### Cost Savings

| Scenario | Without Trimming | With Trimming |
|----------|-----------------|---------------|
| History | 20 turns × 400 tokens = 8,000 tokens | Summary (400 chars ≈ 100 tokens) + last 2 turns (800 tokens) = 900 tokens |
| Token savings | — | 7,100 tokens saved |
| At Flash pricing | $0.000800 | $0.000090 |
| At Max pricing | $0.020000 | $0.002250 |

**Savings per request**: ~89% of history tokens.

### Exact Strategy

```python
def compress_history(history, keep_verbatim=2, max_summary_chars=400):
    if len(history) <= keep_verbatim:
        return list(history)
    older = history[:-keep_verbatim]
    recent = history[-keep_verbatim:]
    joined = " ".join(m.content for m in older)
    summary = joined[:max_summary_chars] + ("..." if len(joined) > 400 else "")
    return [Message(role="system", content=f"Earlier conversation summary: {summary}")] + list(recent)
```

## 3. Model Routing

### What It Does

Instead of sending every request to the flagship model (`qwen3.7-max` at $2.50/1M input), the router analyzes the query difficulty and sends simple queries to the cheapest model.

### Cost Savings

Assuming a typical distribution where 70% of queries are simple, 20% are medium, and 10% are complex:

| Query Type | % of Traffic | Without Routing | With Routing |
|-----------|-------------|----------------|--------------|
| Simple (70%) | 700 queries | Max: $2.50/1M × 700 | Flash: $0.10/1M × 700 |
| Medium (20%) | 200 queries | Max: $2.50/1M × 200 | Plus: $0.40/1M × 200 |
| Complex (10%) | 100 queries | Max: $2.50/1M × 100 | Max: $2.50/1M × 100 |

**Weighted average cost**: Without routing = $2.50/1M. With routing ≈ $0.40/1M. **Savings: ~84%**.

## Which Technique Provides the Largest Savings?

| Technique | Savings Source | Typical Impact |
|-----------|---------------|----------------|
| **Semantic Caching** (Layer 1) | Avoids API calls entirely | **100% per cache hit** (biggest single-request saving) |
| **Model Routing** (Layer 3) | Routes to cheaper models | **84% average** (biggest aggregate saving for new queries) |
| **History Trimming** (Layer 2) | Reduces input tokens | **50–90% of history tokens** (significant for multi-turn) |
| **RAG Reranking** (Layer 2) | Reduces context tokens | **40–80% of RAG tokens** (significant when RAG is used) |

### Ranking by Impact

1. **Semantic Caching** — Biggest saving per hit (100%), but depends on cache hit rate.
2. **Model Routing** — Biggest aggregate saving because it applies to every non-cached request.
3. **History Trimming** — High per-request saving, but only applies to multi-turn conversations.
4. **RAG Reranking** — High per-request saving, but only applies when RAG context is present.

All four techniques **stack**. A request that hits the cache saves 100%. A cache miss that has history trimming + RAG reranking + Flash routing might save 95% compared to the naive baseline. The combination is what makes TokenTrim powerful.

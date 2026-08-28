# 12. Main Problem — What TokenTrim Actually Does

## The Problem Statement

AI API calls are expensive. When using Alibaba's Qwen AI models, the cost grows with:
- The number of tokens in the prompt (input cost)
- The number of tokens in the response (output cost)
- The model tier used (flagship models cost 25× more than cheap models)
- Redundant calls (asking the same question twice costs double)

**TokenTrim is a smart middleware layer that sits between the user and the Qwen AI models and intelligently reduces token usage and API costs.**

## The Architecture

```
User Request
      ↓
┌─────────────────────────────────┐
│         TokenTrim Gateway       │
│                                 │
│  Layer 1: Semantic Cache        │  ← Has this been asked before?
│         ↓ (miss)                │
│  Layer 2: Context Compression   │  ← Can we trim the input?
│         ↓                       │
│  Layer 3: Model Router          │  ← Which is the cheapest model
│         ↓                       │     that can handle this?
│  Qwen API Call                  │
│         ↓                       │
│  Cache the result               │  ← Save for future reuse
│         ↓                       │
│  Log cost + savings             │  ← Dashboard data
└─────────────────────────────────┘
      ↓
Response to User
```

## The Six Cost-Reduction Strategies

### 1. Semantic Caching

**What**: Store previous (question, answer) pairs with their embeddings. When a new question arrives, check if a semantically similar question has already been answered.

**How it saves money**: A cache hit costs $0.00 — no API call is made.

**Implementation**: [`SemanticCache`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L120-L148) with `CACHE_SIMILARITY_THRESHOLD = 0.92`.

### 2. Prompt / Context Trimming (History Compression)

**What**: Older conversation history is summarized into a single short message. Only the most recent turns are kept verbatim.

**How it saves money**: Fewer input tokens = lower cost. A 20-turn conversation might compress from 8,200 to 3,100 tokens.

**Implementation**: [`compress_history()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L22-L47) keeps the last 2 turns and folds older history into a truncated summary.

### 3. RAG Optimization (Chunk Reranking)

**What**: Instead of stuffing all retrieved RAG chunks into the prompt, only the top-k most relevant chunks (based on cosine similarity to the current query) are included.

**How it saves money**: Irrelevant chunks waste tokens. Reranking removes them.

**Implementation**: [`rerank_chunks()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L50-L65) with `top_k=2`.

### 4. Model Routing

**What**: A difficulty scorer analyzes the query and routes it to the cheapest model that can handle it.

**How it saves money**: Simple questions (70%+ of real-world queries) go to `qwen3.5-flash` at $0.10/1M input instead of `qwen3.7-max` at $2.50/1M input — a **25× cost reduction**.

**Implementation**: [`pick_model()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L49-L55) with thresholds at 0.35 and 0.70.

### 5. Model Escalation

**What**: If the initially selected model produces a poor response, the system can escalate to a more capable model.

**How it saves money**: By starting cheap and only escalating when needed, the system avoids paying flagship prices for every request.

**Status**: Documented as a v2 feature; the current MVP routes once without retry.

### 6. Cost-Aware Decisions

**What**: Every decision in the pipeline considers cost. The pricing table in [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L48-L54) drives routing, baseline calculations, and dashboard metrics.

**How it saves money**: The system does not just pick the best model — it picks the **cheapest model that is good enough**.

## The Hackathon Context

TokenTrim is built for the **Bano Qabil × Alibaba Cloud AI Hackathon 2026**. The constraints are:
- Must use Alibaba's Qwen AI models
- Must demonstrate measurable cost savings
- Must work in a live demo (resilience matters)
- Must be technically defensible to judges

The six strategies above combine to create a system where a typical workload that would cost $100 with naive usage might cost $5–$15 with TokenTrim — a **85–95% reduction**.

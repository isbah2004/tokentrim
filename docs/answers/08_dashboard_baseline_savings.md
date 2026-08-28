# 8. Dashboard Baseline — How Do We Calculate Savings?

## The Principle: Honest, Explainable Savings

The savings displayed on the dashboard must answer one question:

> **"How much would this request have cost if we had done nothing smart — no caching, no compression, no routing — and just sent the full, raw request to the most expensive model?"**

That hypothetical cost is the **naive baseline**. The actual cost is what TokenTrim spent. The difference is the saving.

## How the Naive Baseline Is Calculated

The baseline is implemented in [`naive_cost()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L64-L78):

```python
def naive_cost(
    input_tokens: int,
    output_tokens: int,
    uncompressed_input_tokens: int | None = None,
    model: str = config.MODEL_MAX,   # flagship = most expensive
) -> float:
    if uncompressed_input_tokens is None:
        uncompressed_input_tokens = int(input_tokens * UNCOMPRESSED_FACTOR)
    return estimate_cost(model, uncompressed_input_tokens, output_tokens)
```

### The Two Components

1. **Uncompressed tokens** — The input token count *before* TokenTrim's [`compress_history()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L22-L47) and [`rerank_chunks()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py#L50-L65) trimmed it. The pipeline measures this by building the uncompressed prompt and comparing:

   ```python
   # In pipeline.py
   compressed_est = estimate_message_tokens(messages)         # after trimming
   uncompressed_est = estimate_message_tokens(uncompressed_messages)  # before trimming
   ratio = uncompressed_est / max(compressed_est, 1)
   ```

2. **Flagship model pricing** — The baseline always uses `qwen3.7-max` pricing ($2.50/1M input, $7.50/1M output), because that is the most expensive model a "do nothing" approach might use.

### Worked Example

| Metric | Value |
|--------|-------|
| User's query + full history + all RAG chunks (uncompressed) | 8,200 input tokens |
| After TokenTrim compression | 3,100 input tokens |
| Model output | 500 tokens |
| Routed to | `qwen3.5-flash` |

**Naive baseline cost** (uncompressed + flagship):
```
(8,200 × $2.50 + 500 × $7.50) / 1,000,000 = $0.02050 + $0.00375 = $0.02425
```

**Actual cost** (compressed + flash):
```
(3,100 × $0.10 + 500 × $0.40) / 1,000,000 = $0.00031 + $0.00020 = $0.00051
```

**Savings**:
```
$0.02425 - $0.00051 = $0.02374 saved (97.9%)
```

## What the Dashboard Should Display

| Field | Value | Source |
|-------|-------|--------|
| **Baseline Cost** | $0.02425 | `naive_cost_usd` from `ChatResponse` |
| **Actual Cost** | $0.00051 | `cost_usd` from `ChatResponse` |
| **Dollar Saved** | $0.02374 | `naive_cost_usd - cost_usd` |
| **Percentage Saved** | 97.9% | `(naive - actual) / naive × 100` |

## Cache Hits: The "Free" Savings

When a request is served from cache, the actual cost is **$0.00**. The baseline cost is still calculated using [`_baseline_for_cache_hit()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/pipeline.py#L147-L160):

```python
def _baseline_for_cache_hit(self, query, history, rag_chunks) -> float:
    # Build what the uncompressed flagship prompt would have looked like
    uncompressed_messages = build_prompt(self.system_prompt, msg_history, rag_chunks, query)
    input_tokens = estimate_message_tokens(uncompressed_messages)
    return naive_cost(input_tokens=input_tokens, output_tokens=0,
                      uncompressed_input_tokens=input_tokens, model=config.MODEL_MAX)
```

This means every cache hit credits the dashboard with the full flagship cost as a saving, because that is genuinely what was avoided.

## Is This Calculation Defensible?

**Yes**, because:

1. **The baseline is conservative** — It uses the real uncompressed token count (not an inflated estimate) and the real flagship pricing.
2. **The actual cost is exact** — It comes from the API's `usage` response, which reports actual tokens consumed.
3. **Cache hits are genuinely free** — No API call is made; the saving is the real avoided cost.
4. **The `UNCOMPRESSED_FACTOR = 2.6`** is only used as a fallback when the pipeline cannot measure the real uncompressed token count. The pipeline passes the exact ratio whenever possible.

The dashboard is not "making up" savings — it is answering the factual question: "What would this have cost without TokenTrim?"

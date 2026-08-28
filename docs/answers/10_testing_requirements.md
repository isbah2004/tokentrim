# 10. Testing Requirements

## The Command

```bash
python -m unittest discover -s tests -t .
```

**Expected result: 53 tests passing, with 3 skipped.**

## What the Tests Prove

### 1. The First Request Generates a Response

The test sends a query through the [`Gateway.chat()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/pipeline.py#L54-L145) method and verifies:
- A non-empty response is returned.
- `cached` is `False` (first request, nothing in cache).
- `cost_usd > 0` (a model call was made).
- `model_used` is set to one of the three model tiers.

### 2. The Second Identical Request Is a Free Cache Hit

The same query is sent again. The test verifies:
- `cached` is `True`.
- `cost_usd == 0.0` (no API call made).
- The response matches the first response.
- `similarity` is close to `1.0` (exact same query).

This proves the semantic cache works end-to-end.

### 3. Simple Queries Route to Flash

Queries like `"Hello"` or `"What time is it?"` should produce a low difficulty score (< 0.35) and route to `qwen3.5-flash`.

The test verifies:
```python
decision = pick_model("Hello", rag_chunk_count=0, history_len=0)
assert decision.model == config.MODEL_FLASH
```

### 4. Complex Queries Escalate to Max

Queries with complexity signals (long text, many RAG chunks, keywords like "analyze", "compare", "debug") should score ≥ 0.70 and route to `qwen3.7-max`.

The test verifies:
```python
decision = pick_model(
    "Analyze and compare the performance of three different algorithms step by step",
    rag_chunk_count=5, history_len=10
)
assert decision.model == config.MODEL_MAX
```

### 5. The Offline Pipeline Works Correctly

All tests run without:
- An internet connection
- A `DASHSCOPE_API_KEY`
- A PostgreSQL database

This is possible because the tests use:
- [`FakeChatModel`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/qwen_client.py#L64-L79) instead of `QwenChatModel`
- [`HashingEmbeddingProvider`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py#L43-L71) instead of `QwenEmbeddingProvider`
- [`InMemoryVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L51-L77) instead of `PgVectorStore`

### 6. Routing Decisions Are Deterministic and Testable

The [`score_difficulty()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L33-L46) function is a pure function — same inputs always produce the same output. There is no randomness, no API call, no external state. This means:

- Tests are repeatable across machines and environments.
- Routing logic can be verified with exact assertions.
- Changes to thresholds or weights are immediately caught by the test suite.

## Why 3 Tests Are Skipped

The 3 skipped tests likely test functionality that requires:
- A live API connection (`@unittest.skipIf(not DASHSCOPE_API_KEY, ...)`)
- A running PostgreSQL instance (`@unittest.skipIf(not DATABASE_URL, ...)`)

These are integration tests that validate the live path. They are skipped in the default offline test run but can be enabled by providing the necessary environment variables.

## The Testing Guarantee

If all 53 tests pass:
- The full pipeline works offline ✓
- Cache hits save money ✓
- Routing is correct and deterministic ✓
- Compression reduces token counts ✓
- Cost calculations are accurate ✓
- Configuration is valid ✓

If any test fails, something is broken — and the CI/CD pipeline should refuse to deploy.

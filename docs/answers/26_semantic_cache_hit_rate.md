# 26. Semantic Cache Hit Rate

## The Central Question

> When we get a cache hit, can we confidently return the cached answer?

The answer depends entirely on the **similarity threshold** — the value `X` where:

```
Similarity ≥ X → Return cached response
Similarity < X → Send request to model
```

## The Current Threshold

From [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L63):

```python
CACHE_SIMILARITY_THRESHOLD = 0.92
```

This means: only return a cached answer if the cosine similarity between the new query's embedding and the stored query's embedding is **≥ 0.92**.

## Why 0.92?

This is a **conservative** threshold, chosen to minimize false positives:

| Threshold | Behavior |
|-----------|----------|
| 0.99 | Ultra-strict: only near-exact duplicates match. Very few cache hits. |
| **0.92** | **Conservative: strong paraphrases match. Low false-positive risk.** |
| 0.85 | Moderate: looser paraphrases match. Some false positives possible. |
| 0.75 | Aggressive: topically similar questions match. High false-positive risk. |

## The Risk of False Positives

A **false-positive cache hit** occurs when the system returns a cached answer that does not actually answer the new question:

| New Query | Cached Query | Similarity | Same Answer? |
|-----------|-------------|-----------|-------------|
| "What are your hours?" | "When are you open?" | 0.95 | ✅ Yes |
| "What are your hours?" | "What are your opening hours?" | 0.97 | ✅ Yes |
| "What are your return policy?" | "What are your hours?" | 0.78 | ❌ No |
| "What is the meaning of life?" | "What is the purpose of life?" | 0.91 | ⚠️ Maybe |

At threshold 0.92, the fourth pair (0.91) would correctly **not** be a cache hit, even though the queries are related. The system errs on the side of making a new API call rather than returning a wrong answer.

## How to Determine the Right Threshold

### Step 1: Collect Query Pairs

Create a dataset of query pairs labeled as:
- **True paraphrases** (should be cache hits): "What are your hours?" / "When are you open?"
- **False paraphrases** (should NOT be cache hits): "What are your hours?" / "How old are you?"

### Step 2: Embed and Measure Similarity

For each pair, compute the cosine similarity using `text-embedding-v4` at 768 dimensions.

### Step 3: Find the Optimal Threshold

Plot the similarity distribution:

```
True paraphrases:  [0.88, 0.91, 0.93, 0.95, 0.96, 0.97, 0.98]
False paraphrases: [0.45, 0.52, 0.61, 0.68, 0.72, 0.78, 0.82]
```

The threshold should be set where:
- **Most true paraphrases are above it** (high recall for cache hits)
- **All false paraphrases are below it** (zero false positives)

In this example, `0.88` would work. If the false paraphrase distribution extends up to `0.85`, then `0.90` is safer.

### Step 4: Optimize the Trade-Off

```
Higher threshold (e.g., 0.95):
  ✅ Fewer false positives (wrong answers)
  ❌ More false negatives (missed cache hits → unnecessary API calls)

Lower threshold (e.g., 0.85):
  ✅ More cache hits (lower cost)
  ❌ More false positives (wrong answers returned)
```

The optimal threshold depends on the **cost of a wrong answer** vs. the **cost of a missed cache hit**:
- If wrong answers are catastrophic (medical, legal) → use 0.95+
- If wrong answers are merely inconvenient (FAQ bot) → use 0.85–0.90
- TokenTrim's default of 0.92 is a reasonable middle ground for general-purpose use.

## Implementation in TokenTrim

The threshold is applied in [`SemanticCache.lookup()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L131-L143):

```python
def lookup(self, query: str) -> Optional[CacheHit]:
    vec = self.embedder.embed(query)
    result = self.store.nearest(vec)
    if result is None:
        return None
    entry, similarity = result
    if similarity >= self.threshold:  # 0.92 default
        return CacheHit(response=entry.response, similarity=similarity, ...)
    return None
```

The threshold is configurable via `TOKENTRIM_CACHE_THRESHOLD` environment variable, so it can be tuned without code changes.

# 27. Should Cached Answers Be Stored in pgvector?

## The Short Answer

**Yes.** Storing cached answers in pgvector is the right architectural decision for TokenTrim. This is already implemented in [`PgVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L80-L117).

## Benefits of Storing Cached Answers in pgvector

### 1. Avoid Repeated API Calls
When a user asks a semantically similar question, the cached answer is returned directly:
```
Cost per cache hit: $0.00
Cost per API call: $0.0001 – $0.02+ (depending on model and tokens)
```

### 2. Reduce Token Usage
No input tokens are consumed for a cache hit. No output tokens are generated. Total token usage: **zero**.

### 3. Reduce API Costs
With a 30% cache hit rate and 1,000 daily requests:
- 300 requests × $0.02 average = **$6/day saved** from cache hits alone.
- At scale (100K requests/day): **$600/day saved**.

### 4. Reduce Latency
A pgvector nearest-neighbor search with HNSW takes **< 1ms** for small datasets. A model API call takes **200–2000ms**. Cache hits are **200–2000× faster**.

### 5. Improve Scalability
As the cache grows, the hit rate improves (more queries are covered). This creates a **positive feedback loop**: more usage → better cache → lower cost per query.

### 6. Answer Paraphrased Questions Instantly
Unlike exact-match caches (e.g., Redis with string keys), pgvector enables **semantic matching**:
```
"What are your hours?"  →  Matches  →  "When are you open?" (similarity: 0.95)
```

## Risks of Caching Responses

### 1. Cached Answers Can Become Outdated

**Problem**: If the underlying data changes (e.g., business hours change), the cached answer is now wrong.

**Mitigation**:
- **TTL (Time-To-Live)**: Set `expires_at` on cache entries. Expire after 24 hours or 7 days depending on the use case.
- **Manual invalidation**: Provide an API to clear the cache when data changes.
- **Versioning**: Associate cache entries with a data version; invalidate when the version changes.

### 2. Semantically Similar ≠ Same Answer Needed

**Problem**: "What is the weather in London?" and "What is the weather in Paris?" are semantically similar but require different answers.

**Mitigation**:
- **High similarity threshold** (0.92): Only near-exact paraphrases match. Location-specific queries would not match each other at this threshold because "London" and "Paris" are different entities.
- **Context-aware cache keys**: Include relevant parameters (e.g., location, user ID, date) in the cache key, not just the query text.

### 3. False-Positive Cache Hits Return Incorrect Responses

**Problem**: A query matches a cached entry that superficially looks similar but actually asks something different.

**Mitigation**:
- **Conservative threshold** (0.92): Reduces false positives to near-zero for well-tuned embedding models.
- **Confidence display**: Show the user the similarity score and the original cached query, so they can identify false matches.
- **Feedback mechanism**: Allow users to flag incorrect cached responses for removal.

### 4. Similarity Thresholds Are Difficult to Tune

**Problem**: The optimal threshold depends on the embedding model, the domain, and the acceptable error rate.

**Mitigation**:
- **Configurable threshold**: Already implemented via `TOKENTRIM_CACHE_THRESHOLD` environment variable.
- **Empirical tuning**: See [Q26](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/26_semantic_cache_hit_rate.md) for the methodology to determine the optimal threshold.

### 5. Cache Invalidation Is Important

**Problem**: "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

**Mitigation strategies**:

| Strategy | How It Works | When to Use |
|----------|-------------|-------------|
| TTL-based | Entries expire after N hours | Default; works for most cases |
| Version-based | Tag entries with a data version; invalidate on version change | When the underlying data changes periodically |
| Manual purge | API endpoint to clear the cache | After a known data update |
| LRU eviction | Remove least-recently-used entries when cache size exceeds a limit | When storage is constrained |

## The Robust Cache-Validation Strategy

```
New query arrives
       ↓
Embed query → [0.12, -0.34, 0.56, ...]
       ↓
Find nearest neighbor in pgvector
       ↓
Similarity ≥ 0.92?
   ├── NO → Cache miss → Call model → Store (query, response, embedding)
   └── YES
        ↓
   Has the entry expired (TTL)?
   ├── YES → Treat as cache miss → Call model → Update cache entry
   └── NO
        ↓
   Return cached response (cost: $0.00)
```

## Conclusion

Storing cached answers in pgvector is the correct choice. The benefits (cost savings, latency reduction, scalability) far outweigh the risks, especially when the risks are mitigated by:
- A conservative similarity threshold (0.92)
- TTL-based expiration
- The ability to manually invalidate entries

# 9. Can We Ask Questions That Have Already Been Asked?

## Yes — That Is Exactly What the Semantic Cache Does

The semantic cache ([`SemanticCache`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L120-L148)) is designed to detect when a user asks a question that has already been answered, and return the cached response **without making another API call**.

## How It Works

### Step 1: Embed the New Query

When a new query arrives, the system converts it into a vector using the embedding provider:

```python
vec = self.embedder.embed(query)  # 768-dimensional vector
```

### Step 2: Find the Nearest Stored Query

The vector store searches for the most similar previously-stored query:

```python
result = self.store.nearest(vec)  # returns (StoredEntry, similarity_score)
```

### Step 3: Apply the Similarity Threshold

If the similarity is above the threshold (`CACHE_SIMILARITY_THRESHOLD = 0.92`), the cached answer is returned:

```python
if similarity >= self.threshold:
    return CacheHit(response=entry.response, similarity=similarity, ...)
```

### The Complete Flow

```
User asks: "What are your hours?"
       ↓
Embed query → [0.12, -0.34, 0.56, ...]
       ↓
Search vector store for nearest neighbor
       ↓
Found: "When are you open?" (similarity = 0.95)
       ↓
0.95 ≥ 0.92 → CACHE HIT
       ↓
Return stored answer (cost = $0.00)
```

## The Paraphrasing Problem

Exact string matching (`"What are your hours?" == "When are you open?"`) would fail because the strings are different.

**Semantic matching** works because the embedding model (Alibaba's `text-embedding-v4`) maps both queries to nearby points in vector space:

| Query | Embedding (conceptual) |
|-------|----------------------|
| "What are your hours?" | [0.12, -0.34, 0.56, ...] |
| "When are you open?" | [0.11, -0.33, 0.55, ...] |
| "How do I debug Python?" | [-0.45, 0.78, -0.12, ...] |

The first two are close (high cosine similarity). The third is far away (low similarity). This is the fundamental insight that makes semantic caching work.

## Important Limitation: Offline Mode

The [`HashingEmbeddingProvider`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py#L43-L71) used in offline mode only captures **lexical overlap**, not true semantic similarity. Two questions that share no words will not match, even if they mean the same thing:

| Pair | HashingEmbeddingProvider | QwenEmbeddingProvider |
|------|--------------------------|----------------------|
| "What are your hours?" / "What are your hours?" | ✅ Exact match | ✅ Match |
| "What are your hours?" / "What are your opening hours?" | ⚠️ Partial match (shared words) | ✅ Match |
| "What are your hours?" / "When are you open?" | ❌ Low overlap | ✅ Match |

This is why **true semantic caching requires the live `text-embedding-v4` model**. The offline hashing provider is for testing the cache *mechanics*, not the semantic *quality*.

## The Answer

Yes, the system can answer previously-asked questions — and it does so:
- **For free** (no API call)
- **Instantly** (vector lookup instead of model generation)
- **For paraphrased questions** (when using the live embedding model)

This is one of TokenTrim's primary cost-saving mechanisms.

# 21. IVFFLAT Indexing

## Why Are We Using IVFFLAT?

IVFFLAT (Inverted File with Flat quantization) is the indexing method currently used by the [`PgVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L80-L117) for approximate nearest-neighbor (ANN) search in pgvector.

The SQL from the schema setup:

```sql
CREATE INDEX idx_cache_embedding
    ON tokentrim_cache
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

## How IVFFLAT Works

1. **Training phase**: The dataset is partitioned into `lists` clusters using k-means. Each cluster has a centroid.
2. **Insertion**: Each new vector is assigned to its nearest centroid's cluster.
3. **Search**: Instead of scanning all vectors, only the `probes` nearest clusters are searched.

```
All vectors (1000)
    ↓ k-means
100 clusters (10 vectors each, on average)
    ↓ search query arrives
Find nearest 3 cluster centroids
    ↓
Scan only 30 vectors (instead of 1000)
    ↓
Return nearest neighbor
```

## IVFFLAT vs. HNSW: The Key Comparison

| Factor | IVFFLAT | HNSW |
|--------|---------|------|
| **Index build time** | Fast (one k-means pass) | Slow (builds multi-layer graph) |
| **Recall** | Good (depends on `lists` and `probes`) | Excellent (typically 99%+) |
| **Query latency** | Fast | Faster (for high-recall) |
| **Memory** | Lower (stores centroids + flat vectors) | Higher (stores graph edges) |
| **Insert performance** | Requires periodic re-indexing after many inserts | Inserts update the graph incrementally |
| **Parameter tuning** | `lists` (at build) + `probes` (at query) | `m` (connections) + `ef_construction` (build quality) |
| **Best for** | Static or slowly-changing datasets | Dynamic datasets with frequent inserts |
| **pgvector support** | Yes (since v0.1) | Yes (since v0.5) |

## When IVFFLAT Is the Right Choice

IVFFLAT is appropriate when:
- ✅ The dataset is **small to medium** (< 100K vectors)
- ✅ The dataset is **relatively static** (few inserts after initial load)
- ✅ **Build time matters** (quick to set up for a hackathon)
- ✅ **Memory is constrained** (smaller index footprint)

## When HNSW Is Better

HNSW is better when:
- ✅ **High recall is critical** (semantic cache false negatives are costly)
- ✅ The dataset grows **dynamically** (new queries cached continuously)
- ✅ You cannot afford to **rebuild the index** periodically
- ✅ **Query latency must be consistently low** regardless of dataset size

## The Balance of Factors

| Factor | IVFFLAT | HNSW | Winner for TokenTrim |
|--------|---------|------|---------------------|
| Recall | ~95% (well-tuned) | ~99% | HNSW |
| Query latency | ~1–5ms | ~0.5–2ms | HNSW |
| Index build time | Seconds | Minutes | IVFFLAT |
| Memory | Lower | ~2–3× more | IVFFLAT |
| Insert/update | Needs rebuild | Incremental | HNSW |
| Scalability | Good to ~100K | Good to ~10M | HNSW |

## Other ANN Indexing Approaches

| Method | Description | Pros | Cons |
|--------|-------------|------|------|
| **Flat (brute force)** | Scan all vectors | 100% recall, simple | O(N) per query, slow at scale |
| **IVFFLAT** | Cluster + flat search | Fast build, low memory | Needs reindex, recall depends on tuning |
| **HNSW** | Hierarchical navigable small world graph | High recall, fast queries, dynamic | Higher memory, slow build |
| **IVF-PQ** | Cluster + product quantization | Very compact, fast at scale | Lower recall, lossy compression |
| **ScaNN** | Google's learned quantization + reranking | State-of-the-art recall/speed | Not available in pgvector |

## Recommendation for TokenTrim

### Hackathon MVP: IVFFLAT ✅
- Quick to set up.
- Small dataset (< 1K cached queries during a demo).
- Works with the current schema.

### Production: Migrate to HNSW
```sql
-- Drop IVFFLAT index
DROP INDEX idx_cache_embedding;

-- Create HNSW index
CREATE INDEX idx_cache_embedding
    ON tokentrim_cache
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

HNSW handles dynamic inserts (new queries are continuously cached) without requiring periodic reindexing, making it the better long-term choice.

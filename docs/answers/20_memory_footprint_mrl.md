# 20. Memory Footprint and Matryoshka Representation Learning (MRL)

## What Is Matryoshka Representation Learning?

**Matryoshka Representation Learning (MRL)** is a training technique introduced by Kusupati et al. (2022) that produces embeddings where **the first `d` dimensions are a valid, self-contained embedding of dimension `d`**.

The name comes from Russian Matryoshka (nesting) dolls — smaller dolls fit inside larger ones, and each is complete in itself.

### How It Works

A standard embedding model produces a single fixed-size vector (e.g., 2048 dimensions). To get a smaller vector, you would need to retrain a separate model.

With MRL, the model is trained with a **multi-scale loss function**:

```
During training, the loss is computed at multiple truncation points:

L_total = L(d=2048) + L(d=1024) + L(d=768) + L(d=512) + L(d=256)

Each L(d) computes the contrastive/similarity loss using only
the first d dimensions of the embedding.
```

This forces the model to encode the **most important semantic information** in the early dimensions. Dimension 1 captures the broadest distinction, dimension 2 adds the next most important feature, and so on.

### The Result

You train **one model** but get **many embedding sizes** for free:

```
Full embedding:  [d1, d2, d3, d4, ..., d768, ..., d1024, ..., d2048]
                  ├──────── 256 ──────────┤
                  ├──────────── 512 ──────────────┤
                  ├──────────────── 768 ──────────────────┤
                  ├────────────────────── 1024 ──────────────────────┤
                  ├─────────────────────────── 2048 ─────────────────────────────┤
```

Just truncate the vector to the desired length. No retraining needed.

## Why MRL Matters for TokenTrim

### Direct Impact on Hardware Requirements

| Dimension | RAM per 100K vectors | Index RAM (IVFFLAT) | Disk per 100K |
|-----------|---------------------|--------------------|----|
| 2048 | ~800 MB | ~1.6 GB | ~800 MB |
| 1024 | ~400 MB | ~800 MB | ~400 MB |
| **768** | **~300 MB** | **~600 MB** | **~300 MB** |
| 512 | ~200 MB | ~400 MB | ~200 MB |
| 256 | ~100 MB | ~200 MB | ~100 MB |

For a hackathon running on a small VPS or laptop, the difference between 800 MB and 300 MB is significant.

### Search Performance

Cosine similarity computation scales linearly with dimension:

```
Time ∝ d (embedding dimension)
```

768-dim vectors are **62.5% faster** to compare than 2048-dim vectors. For brute-force search (used by [`InMemoryVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L64-L74)), this directly reduces cache lookup latency.

### API Cost

Alibaba's `text-embedding-v4` supports dimension selection via the `dimensions` parameter:

```python
resp = client.embeddings.create(
    model="text-embedding-v4",
    input=texts,
    dimensions=768  # MRL truncation
)
```

Smaller dimensions may reduce API cost (depends on provider pricing), and definitely reduce network transfer time.

## The Optimal Trade-Off: Accuracy vs. Memory vs. Latency

```
         Accuracy
            ▲
    100% ───┤  ●───────●───────●
            │  2048   1024    768  ← Diminishing returns
     95% ───┤                          ●
            │                         512
     90% ───┤                                ●
            │                               256
            └───────────────────────────────────► Memory Savings
              0%      50%     62.5%   75%   87.5%
```

The key finding from MRL research:
- Going from 2048 → 768 loses only **1–3% accuracy** on standard retrieval benchmarks.
- Going from 768 → 256 loses **5–10% accuracy**.
- The "elbow point" is typically around 512–768 dimensions.

## How to Determine the Optimal Dimension for TokenTrim

1. **Take the benchmark query pairs** from the routing benchmark (see [Q16](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/16_determining_routing_values.md)).
2. **Embed at all five dimensions** using `text-embedding-v4`.
3. **Measure Recall@1** for cache hit detection at each dimension.
4. **Measure latency** for nearest-neighbor search at each dimension.
5. **Pick the smallest dimension where Recall@1 ≥ 95%**.

If 512 achieves 95% recall, switch to 512 and save another 33% storage. If 768 is needed for 95% recall, the current setting is validated.

## Summary

MRL is not just a theoretical concept — it is the specific technology that allows TokenTrim to use 768-dimensional embeddings from a model that natively produces 2048 dimensions, saving 62.5% on storage, memory, and compute with minimal quality loss. Understanding MRL is essential because it justifies the `EMBED_DIM = 768` setting and defines the design space for further optimization.

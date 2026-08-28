# 19. Embedding Dimension — Why `EMBED_DIM = 768`?

## The Setting

From [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L39-L41):

```python
EMBED_MODEL = "text-embedding-v4"
EMBED_DIM = 768
```

Alibaba's `text-embedding-v4` supports **Matryoshka Representation Learning (MRL)**, which means the same model can produce embeddings of different dimensions:

```
2048 → Full resolution (most accurate)
1024 → High resolution
 768 → Selected by TokenTrim
 512 → Compact
 256 → Minimal
```

## Why 768 and Not 1024 or 2048?

### Storage Savings

| Dimension | Bytes per vector (float32) | Reduction vs 1024 | Reduction vs 2048 |
|-----------|---------------------------|--------------------|--------------------|
| 2048 | 8,192 bytes | — | — |
| 1024 | 4,096 bytes | — | 50% smaller |
| **768** | **3,072 bytes** | **25% smaller** | **62.5% smaller** |
| 512 | 2,048 bytes | 50% smaller | 75% smaller |
| 256 | 1,024 bytes | 75% smaller | 87.5% smaller |

### Index Size

For 100,000 cached queries:

| Dimension | Vector data alone |
|-----------|-------------------|
| 2048 | ~800 MB |
| 1024 | ~400 MB |
| **768** | **~300 MB** |
| 512 | ~200 MB |

Smaller indexes fit in RAM, which means faster ANN lookups.

### Similarity Computation Speed

Cosine similarity between two vectors requires `N` multiplications and `N` additions. With 768 dimensions, this is **25% faster** than 1024 and **62.5% faster** than 2048.

For the brute-force [`InMemoryVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L64-L74), this directly impacts lookup latency.

### Why Not 512 or 256?

Reducing below 768 starts to noticeably degrade semantic retrieval quality. At 256 dimensions, the embedding space is too compressed to distinguish between subtly different meanings:

- "What are your hours?" vs "What are your opening hours?" — still close at 768
- "What are your hours?" vs "How many hours do you work?" — might blur at 256

768 is the **"sweet spot"** where:
- Storage is significantly reduced vs 1024/2048
- Retrieval quality remains high for the semantic cache's use case
- It is a widely-used default (BERT's original embedding size was 768)

## The Trade-Off

```
     Quality ◄─────────────────────────────────────► Efficiency
     2048        1024        768        512        256
     │            │          │          │          │
     ▼            ▼          ▼          ▼          ▼
  Best recall   Good      Good w/    Acceptable  Lossy
  Highest cost  Balance   lower cost  Budget      Minimal
```

## What Should Be Investigated

The document asks:

> **What is the actual retrieval-quality difference between 2048, 1024, 768, 512, and 256 dimensions for our specific use case?**

The experiment:

1. Take 100 query pairs with known semantic similarity (e.g., paraphrases → similar; unrelated → dissimilar).
2. Embed all queries at each dimension.
3. Compute cosine similarity for each pair at each dimension.
4. Measure:
   - **Recall@1**: Does the nearest neighbor in the cache match the correct paraphrase?
   - **False positive rate**: Do unrelated queries incorrectly match?
5. Compare results across dimensions.

If 512 achieves 98% of the recall of 768, TokenTrim could reduce storage by another 33%. If 768 achieves 99% of the recall of 1024, the current choice is validated.

## The Current Decision Is Sound

768 dimensions is a well-justified default:
- Proven effective in the NLP community (BERT, all-MiniLM, etc.)
- Significant storage savings over 1024/2048
- Minimal quality loss for the semantic cache use case
- Configurable via `TOKENTRIM_EMBED_DIM` environment variable if experimentation shows a better value

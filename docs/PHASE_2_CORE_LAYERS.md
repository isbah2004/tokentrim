# Phase 2 — Core Layers

The heart of TokenTrim: the three optimization layers, plus the embedding
providers and stats aggregation they depend on. Per the build guide, each layer
is built and **unit-tested independently** before anything is wired together.

## What this phase delivers

| Module | Layer | Responsibility |
|---|---|---|
| `app/embeddings.py` | (shared) | Text → vector. `QwenEmbeddingProvider` (prod) + `HashingEmbeddingProvider` (offline). |
| `app/cache.py` | **1 — Semantic Cache** | Skip generation for repeats/paraphrases. `SemanticCache` + `InMemoryVectorStore` + `PgVectorStore`. |
| `app/compressor.py` | **2 — Context Compressor** | Trim history, rerank RAG chunks, build the final prompt. |
| `app/router.py` | **3 — Model Router** | Score difficulty, pick the cheapest capable tier, cost math. |
| `app/stats.py` | (shared) | Append request logs; aggregate cost, baseline, savings, hit rate. |
| `app/vectormath.py` | (shared) | Pure-Python cosine similarity (no numpy dependency). |

## The design decision that makes it all testable: dependency injection

Every external dependency is injected behind a tiny interface, so the whole
core runs offline with fakes:

- `SemanticCache(store, embedder, threshold)` — the store and embedder are
  parameters. Tests pass an `InMemoryVectorStore` and a fixed-vector fake
  embedder, so **threshold behaviour is verified exactly** without a database
  or an API key.
- `QwenEmbeddingProvider` and `PgVectorStore` **import `openai` / `psycopg2`
  lazily**, so importing `app.cache` or `app.embeddings` never requires those
  packages. The test suite never touches them.
- `stats.log_request` / `get_summary` take the log-file path as an argument, so
  tests point them at a temp file.

## Layer notes

- **Semantic cache** matches on *meaning*, which is what distinguishes it from
  Model Studio's implicit *prefix* cache. The offline `HashingEmbeddingProvider`
  uses signed feature hashing: identical text → cosine 1.0, shared-token text →
  high similarity. It deliberately does **not** model deep semantics (that's
  `text-embedding-v4`'s job in production) — it exists to exercise the cache
  mechanics without a network.
- **Compressor** keeps the last N turns verbatim and summarises the rest, keeps
  only the top-k RAG chunks, and orders the prompt (stable content first,
  question last) to stay prefix-cache friendly.
- **Router** scores difficulty from query length, retrieved-context size,
  history depth, and hard-signal keywords, then maps the score to a tier using
  the `config` thresholds. The cost helpers (`estimate_cost`, `naive_cost`)
  drive the dashboard's before/after numbers and are pinned to the build
  guide's worked example in the tests.

## Verifying this phase

```bash
python -m unittest discover -s tests -t .
```

Expected: **44 tests pass** (config + embeddings + cache + compressor + router +
stats). Notable checks:

- `test_router.py::test_worked_example_reconciles` — the optimized call costs
  exactly **$0.00043**, matching the guide.
- `test_cache.py` — exact duplicate → hit at similarity 1.0; a 0.96-similar
  query hits at threshold 0.92 but misses at 0.98.

---

**Previous:** [Phase 1 — Foundation](PHASE_1_FOUNDATION.md) ·
**Next:** [Phase 3 — Gateway & Dashboard](PHASE_3_GATEWAY_DASHBOARD.md).

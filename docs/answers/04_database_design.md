# 4. Database Design

## What Type of Database Should We Use?

TokenTrim has two distinct data storage needs:

| Need | Best Fit | Why |
|------|----------|-----|
| **Vector similarity search** (semantic cache) | **PostgreSQL + pgvector** | Stores embeddings alongside query/response text; supports cosine distance search with ANN indexes; the team already uses it via [`PgVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L80-L117). |
| **Request logs / stats** | **JSONL file** (MVP) or **PostgreSQL table** (production) | Currently [`stats.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/stats.py) writes to a JSONL file. For production, a `tokentrim_logs` table in the same Postgres instance avoids adding infrastructure. |

### Why PostgreSQL + pgvector (Not a Dedicated Vector DB)

- **One database, not two** — Avoids the operational complexity of maintaining a separate Pinecone/Weaviate/Qdrant instance alongside a relational DB.
- **ACID transactions** — Cache insertions and reads are transactional; no risk of partial writes.
- **SQL flexibility** — Analytics queries (cost summaries, routing breakdowns) run against the same database.
- **pgvector maturity** — pgvector 0.7+ supports both IVFFLAT and HNSW indexes and is production-proven at scale.

## What Should the Schema Look Like?

### Semantic Cache Table

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE tokentrim_cache (
    id          BIGSERIAL PRIMARY KEY,
    query       TEXT NOT NULL,
    response    TEXT NOT NULL,
    embedding   vector(768) NOT NULL,   -- matches EMBED_DIM = 768
    created_at  DOUBLE PRECISION NOT NULL,
    expires_at  DOUBLE PRECISION,       -- for TTL-based invalidation
    hit_count   INTEGER DEFAULT 0       -- track cache utility
);

-- ANN index for fast nearest-neighbor lookup
CREATE INDEX idx_cache_embedding
    ON tokentrim_cache
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Request Logs Table (Production Upgrade)

```sql
CREATE TABLE tokentrim_logs (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    cache_hit       BOOLEAN NOT NULL,
    model           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cached_tokens   INTEGER DEFAULT 0,
    cost_usd        DOUBLE PRECISION,
    naive_cost_usd  DOUBLE PRECISION,
    latency_ms      DOUBLE PRECISION,
    routing_reason  TEXT
);
```

## Which Data Needs to Be Stored?

| Data | Where | Purpose |
|------|-------|---------|
| User query text | `tokentrim_cache.query` | Display original query on cache hit |
| Model response text | `tokentrim_cache.response` | Return cached answer |
| Query embedding (768-dim) | `tokentrim_cache.embedding` | Cosine similarity search |
| Timestamp | `tokentrim_cache.created_at` | TTL expiration, freshness |
| Per-request metrics | `tokentrim_logs` | Dashboard: cost, savings, latency, model used |

## How Should Vectors Be Stored?

pgvector's `vector(768)` type stores the embedding as a native array of 32-bit floats. This is what the current [`PgVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L88-L96) does:

```python
cur.execute(
    "INSERT INTO tokentrim_cache (query, response, embedding, created_at) "
    "VALUES (%s, %s, %s::vector, %s)",
    (query, response, embedding, time.time()),
)
```

The `<=>` operator computes cosine distance, and `1 - distance` gives similarity.

## How Should Cached Responses Be Stored?

Cached responses are stored as plain `TEXT` in the same row as the query and embedding. This co-location means a cache hit requires exactly **one index lookup + one row fetch** — no joins.

## How Should Metadata Be Structured?

Metadata (hit count, expiration, model that generated the response) should be columns on the same table, not a separate metadata store. This keeps queries simple and atomic.

## How Will the Database Scale?

| Scale Factor | Strategy |
|--------------|----------|
| **Rows (cache entries)** | IVFFLAT or HNSW index keeps lookup at O(√N) or O(log N) |
| **Embedding dimension** | Using 768 instead of 2048 reduces storage by 62% |
| **Stale entries** | TTL-based expiration (`expires_at`) + periodic `DELETE` |
| **Read throughput** | Connection pooling (PgBouncer) + read replicas |
| **Write throughput** | Batch inserts; async logging |

## What Indexing Strategy Should We Use?

For the hackathon MVP, **IVFFLAT** is appropriate (small dataset, fast index build). For production, **HNSW** is recommended (better recall, no need to retrain after inserts). See [Question 21](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/21_ivfflat_indexing.md) for a detailed comparison.

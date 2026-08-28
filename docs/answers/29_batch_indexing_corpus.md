# 29. Batch Indexing and Corpus Processing

## The Problem

When TokenTrim needs to process a large knowledge base for RAG (e.g., thousands of documents), it must:

1. Split documents into chunks
2. Embed each chunk (API call per batch)
3. Store the embeddings in the vector database
4. Build an index for fast search
5. Handle additions, deletions, and updates over time

## How Industry Systems Handle Large-Scale Corpus Indexing

### 1. Batch Embedding

Documents are embedded in **batches**, not one at a time. This is critical because:
- API calls have per-request overhead (network latency, connection setup).
- Embedding APIs accept batch inputs (multiple texts in one call).
- Batch processing can be parallelized across workers.

```python
# Single embedding (slow)
for chunk in chunks:
    embedding = embed(chunk)  # 1 API call per chunk

# Batch embedding (fast)
for batch in chunks_batched(chunks, batch_size=100):
    embeddings = embed_batch(batch)  # 1 API call per 100 chunks
```

TokenTrim's [`embed_batch()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py#L89-L93) already supports this:

```python
def embed_batch(self, texts: List[str]) -> List[List[float]]:
    resp = self._get_client().embeddings.create(
        model=self.model, input=texts, dimensions=self.dim
    )
    return [item.embedding for item in resp.data]
```

### 2. Batch Insertion

Embeddings are inserted into the database in bulk:

```sql
-- Single insert (slow)
INSERT INTO tokentrim_cache (query, response, embedding) VALUES (...);

-- Batch insert (fast)
INSERT INTO tokentrim_cache (query, response, embedding) VALUES
  (...), (...), (...), ... ;

-- Or using COPY (fastest for PostgreSQL)
COPY tokentrim_cache (query, response, embedding) FROM STDIN;
```

### 3. Index Building

Indexes are built **after** the bulk data is loaded, not during insertion:

```sql
-- Step 1: Insert all data WITHOUT an index (fast)
COPY tokentrim_cache FROM ...;

-- Step 2: Build the index ONCE (much faster than incremental)
CREATE INDEX idx_cache_embedding
    ON tokentrim_cache
    USING hnsw (embedding vector_cosine_ops);
```

Building the index after all data is loaded is **10–100× faster** than inserting with the index in place, because the index doesn't need to be restructured after each insertion.

### 4. Index Rebuilding

Production systems rebuild indexes periodically for two reasons:
- **IVFFLAT**: Centroids become stale after many insertions.
- **Statistics**: PostgreSQL's query planner needs fresh statistics.

```sql
-- Rebuild index without blocking queries
REINDEX INDEX CONCURRENTLY idx_cache_embedding;

-- Update statistics
ANALYZE tokentrim_cache;
```

### 5. Adding New Documents

New documents are embedded and inserted incrementally:

```
New document arrives
       ↓
Split into chunks
       ↓
Embed chunks (batch API call)
       ↓
INSERT into database
       ↓
HNSW index updates incrementally (no rebuild needed)
```

With HNSW, new vectors are added to the graph without requiring a full rebuild. This is one of HNSW's key advantages over IVFFLAT.

### 6. Handling Deleted Documents

When documents are removed from the knowledge base:

```sql
-- Mark as deleted (soft delete)
UPDATE tokentrim_corpus SET deleted = TRUE WHERE doc_id = 'xyz';

-- Physically remove
DELETE FROM tokentrim_corpus WHERE doc_id = 'xyz';

-- Reclaim space (periodic maintenance)
VACUUM tokentrim_corpus;
```

The index continues to work; deleted vectors are simply excluded from results.

### 7. Incremental Indexing

The industry standard for incremental updates:

```
Track document hashes (content fingerprint)
       ↓
On update run:
  For each document:
    Compute hash
    ├── Hash matches stored hash → Skip (unchanged)
    ├── Hash missing → New document → Embed and insert
    └── Hash differs → Updated document → Re-embed and update
```

This avoids re-embedding the entire corpus when only a few documents change.

### 8. Avoiding Full Rebuilds

| Strategy | How It Works |
|----------|-------------|
| **Content hashing** | Only re-embed documents whose content has changed |
| **HNSW index** | Supports incremental inserts without rebuild |
| **Concurrent reindex** | Rebuild in the background without downtime |
| **Change data capture** | Track which documents changed since last indexing |
| **Timestamp filtering** | Only process documents modified after the last index run |

## The Industry-Standard Pipeline

```
Batch Embedding
      ↓
  ┌─────────────────────────────────┐
  │ 1. Load documents               │
  │ 2. Split into chunks            │
  │ 3. Hash each chunk              │
  │ 4. Skip unchanged chunks        │
  │ 5. Embed new/changed chunks     │
  │    (batch API calls, 100/batch) │
  └─────────────────────────────────┘
      ↓
Batch Insert
      ↓
  ┌─────────────────────────────────┐
  │ 1. COPY or batch INSERT         │
  │ 2. Delete removed chunks        │
  │ 3. VACUUM + ANALYZE             │
  └─────────────────────────────────┘
      ↓
Index Build / Update
      ↓
  ┌─────────────────────────────────┐
  │ Initial load: Build index after │
  │ Incremental: HNSW auto-updates  │
  │ Periodic: REINDEX CONCURRENTLY  │
  └─────────────────────────────────┘
```

## For TokenTrim

The semantic cache currently indexes **queries and responses** (not a document corpus). However, if TokenTrim expands to manage RAG document embeddings, this batch pipeline would apply directly.

For the current cache use case:
- Entries are inserted one at a time (on each cache miss) — this is fine for small scale.
- HNSW index handles incremental inserts natively.
- No batch processing is needed for the cache at hackathon scale.

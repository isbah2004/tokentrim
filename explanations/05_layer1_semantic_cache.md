# 05 — Layer 1: The Semantic Cache
> **Level:** Beginner–Intermediate. You'll understand this even without knowing Python deeply.

---

## 🎯 One-Line Summary

Before asking the AI anything, check if you've already answered something **close enough** to this question. If yes, return that answer instantly — for free.

---

## 🧠 The Core Idea: Meaning-Based Matching

Regular caching (like browser caching) works on **exact matches**:
- Cached: "What are your business hours?"
- New query: "What are your business hours?" → ✅ Cache hit (identical)
- New query: "When are you open?" → ❌ Cache miss (different words, even though it means the same thing)

**Semantic caching** works on **meaning**:
- Cached: "What are your business hours?"
- New query: "When are you open?" → ✅ Cache hit! (same meaning, different words)
- New query: "How do I reset my password?" → ❌ Cache miss (genuinely different question)

This is the power of **embeddings** (introduced in File 02). Two sentences with the same meaning produce very similar number vectors, and we can mathematically measure that similarity.

---

## 🔢 How Similarity is Measured (Cosine Similarity)

When you compare two embedding vectors, you get a **similarity score** between 0 and 1:

| Score | Meaning |
|---|---|
| 1.0 | Identical meaning (exact same sentence) |
| 0.95 | Very similar meaning (paraphrases) |
| 0.80 | Somewhat related topics |
| 0.50 | Vaguely related |
| 0.0 | Completely unrelated |

TokenTrim uses a **threshold of 0.92**. If the best matching cached question has a similarity ≥ 0.92, it's "close enough" — return that cached answer.

> **Why 0.92?** It's a balance. Too high (0.99) and you'll miss obvious paraphrases. Too low (0.80) and you'll return wrong answers for merely-related questions. 0.92 is a reasonable starting point that the guide recommends validating against real question pairs from your own data.

---

## 💾 Where the Cache Lives (PostgreSQL + pgvector)

The cache is stored in a PostgreSQL database table called `tokentrim_cache`:

```sql
CREATE TABLE tokentrim_cache (
    id          SERIAL PRIMARY KEY,      -- auto-incrementing ID
    query       TEXT NOT NULL,           -- the original question text
    response    TEXT NOT NULL,           -- the AI's answer we cached
    embedding   VECTOR(768) NOT NULL,    -- the 768-number vector for the question
    created_at  DOUBLE PRECISION NOT NULL -- when it was stored (Unix timestamp)
);
```

**pgvector** is a PostgreSQL extension that adds the `VECTOR` data type and lets you search for the nearest neighbor vector efficiently.

The `<=>` operator in pgvector computes cosine distance:
```sql
SELECT 1 - (embedding <=> query_vector) AS similarity
```
- `embedding <=> query_vector` = cosine distance (0 = identical, 2 = opposite)
- `1 - distance` = cosine similarity (1 = identical, -1 = opposite)

---

## 📖 The Code, Explained Line by Line

Here's [`app/cache.py`](../app/cache.py) broken down:

### Part 1: Setup

```python
import os
import time
from dataclasses import dataclass
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
```

- `os` — reads environment variables (like the API key)
- `time` — used for timestamps
- `dataclass` — a shortcut for creating simple Python data classes
- `OpenAI` — the Alibaba-compatible API client
- `psycopg2` — the Python library for talking to PostgreSQL

```python
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
```

This creates a client that talks to **Alibaba's Model Studio** but using the **OpenAI format**. Alibaba made their API compatible with OpenAI's so you can use the same code.

```python
EMBED_MODEL = "text-embedding-v4"
EMBED_DIM = 768
```

- The model used to convert text to vectors: `text-embedding-v4` (Alibaba's own)
- We use 768 dimensions (the vector will have 768 numbers)
- Why 768? It's a balance between accuracy (more dimensions = more info) and speed/storage (fewer dimensions = faster search, less disk)

---

### Part 2: The CacheHit Dataclass

```python
@dataclass
class CacheHit:
    response: str       # the cached answer text
    similarity: float   # how similar (0-1) the matched question was
    original_query: str # what the original cached question was
```

This is just a simple container for returning results. When the cache finds a match, it packages these three things together.

---

### Part 3: The SemanticCache Class

```python
class SemanticCache:
    def __init__(self, db_conn, similarity_threshold: float = 0.92):
        self.db = db_conn          # the PostgreSQL connection
        self.threshold = similarity_threshold  # 0.92 by default
```

The class is initialized with:
- A database connection (so it can query the `tokentrim_cache` table)
- A threshold (defaulting to 0.92 — can be tuned)

---

### Part 4: The `_embed` Method (Converting Text → Numbers)

```python
def _embed(self, text: str) -> list[float]:
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=[text],
        dimensions=EMBED_DIM,
    )
    return resp.data[0].embedding
```

This calls the Alibaba API:
- Send the text string
- Get back 768 numbers (a `list[float]`)
- This is the "meaning fingerprint" of the text

This IS an API call and DOES cost tokens (embedding tokens are very cheap — $0.05/1M tokens for text-embedding-v4), but it's tiny compared to what you'd spend generating a full response.

---

### Part 5: The `lookup` Method (Searching for Matches)

```python
def lookup(self, query: str) -> CacheHit | None:
    vec = self._embed(query)          # Step 1: embed the incoming query
    with self.db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT query, response, 1 - (embedding <=> %s::vector) AS similarity
            FROM tokentrim_cache
            ORDER BY embedding <=> %s::vector   -- order by closest first
            LIMIT 1                              -- only the best match
            """,
            (vec, vec),
        )
        row = cur.fetchone()
    if row and row["similarity"] >= self.threshold:
        return CacheHit(
            response=row["response"],
            similarity=row["similarity"],
            original_query=row["query"],
        )
    return None  # No match good enough → cache miss
```

Step by step:
1. Convert the query to a 768-number vector
2. Run a SQL query: "find the row in `tokentrim_cache` whose embedding is most similar to this vector"
3. pgvector's `<=>` operator does this efficiently
4. If the best match has similarity ≥ 0.92 → return it as a `CacheHit`
5. Otherwise → return `None` (cache miss, continue to Layers 2 and 3)

---

### Part 6: The `store` Method (Saving New Answers)

```python
def store(self, query: str, response: str) -> None:
    vec = self._embed(query)
    with self.db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tokentrim_cache (query, response, embedding, created_at)
            VALUES (%s, %s, %s::vector, %s)
            """,
            (query, response, vec, time.time()),
        )
    self.db.commit()
```

After the AI answers a question (that was a cache miss), we:
1. Embed the question
2. Save the question text, the AI's answer, the embedding, and timestamp
3. Next time someone asks something similar, `lookup` will find it

---

## ⚡ Performance: The IVFFlat Index

```sql
CREATE INDEX ON tokentrim_cache USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

Without an index, searching for the nearest vector in a table of 10,000 rows means comparing your query against all 10,000 rows — slow.

**IVFFlat** (Inverted File with Flat quantization) is an index that groups vectors into clusters, so the search only needs to check a fraction of the rows. Much faster for large caches.

> Note from the guide: "Build this index once you have >1000 rows — it actually slows things down on tiny tables."

---

## 📈 What Happens at the Threshold Edge?

What if a question scores 0.91 — just below the threshold?

- The cache lookup returns `None`
- The question goes through Layers 2 and 3 (full processing)
- The model generates a response
- That response is stored back in the cache
- Now, very similar future questions will get a higher score and hit the cache

Over time, the cache gets richer and the hit rate grows. This is why FAQ-heavy applications benefit enormously — the same questions get asked repeatedly.

---

## ✅ Key Takeaways

- The semantic cache converts questions to 768-number vectors and stores them in PostgreSQL
- It matches new questions to cached ones by meaning, not exact text
- A 0.92 similarity threshold is the "close enough" cutoff
- Cache hits bypass the AI model entirely → essentially free responses
- Each answered question is stored back, so the cache grows and improves over time

---

➡️ **Next: [06 — Layer 2: The Context Compressor](./06_layer2_context_compressor.md)**

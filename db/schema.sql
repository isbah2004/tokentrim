-- TokenTrim semantic-cache schema (Postgres + pgvector).
-- Run once against the database named in DATABASE_URL:
--     psql "$DATABASE_URL" -f db/schema.sql
--
-- The VECTOR dimension must match app.config.EMBED_DIM (default 768). If you
-- change EMBED_DIM, change the VECTOR(...) size here to match.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tokentrim_cache (
    id          SERIAL PRIMARY KEY,
    query       TEXT NOT NULL,
    response    TEXT NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    created_at  DOUBLE PRECISION NOT NULL
);

-- IVFFlat index for fast approximate nearest-neighbour search. It only helps
-- once the table has a few thousand rows; below that, a sequential scan is
-- actually faster, so don't be alarmed if the planner ignores it early on.
CREATE INDEX IF NOT EXISTS tokentrim_cache_embedding_idx
    ON tokentrim_cache
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

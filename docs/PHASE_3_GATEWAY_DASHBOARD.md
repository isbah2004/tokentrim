# Phase 3 — Gateway & Dashboard

The three layers become one product: a gateway that runs a request through
cache → compress → route → generate → log, an HTTP API, and a live dashboard
that shows the savings in real dollars.

## What this phase delivers

| File | Purpose |
|---|---|
| `app/pipeline.py` | `Gateway` — orchestrates the three layers and logs each request. The testable core. |
| `app/qwen_client.py` | `ChatModel` interface: `QwenChatModel` (prod, lazy `openai`) + `FakeChatModel` (offline). |
| `app/tokens.py` | Rough offline token estimation (for the fake model + the baseline ratio). |
| `app/main.py` | FastAPI `/chat`, `/stats`, and `/` (dashboard). Thin shell over `Gateway`. |
| `static/dashboard.html` | Chart.js dashboard: KPI tiles + naive-vs-actual cost bars, polling `/stats`. |
| `scripts/batch_index_corpus.py` | Off-the-hot-path batch embedding job. |

## Architecture: a thin HTTP shell over a testable core

`Gateway` takes its collaborators (`SemanticCache`, `ChatModel`) as constructor
arguments. The **same class** runs:

- in **production** — `QwenChatModel` + `QwenEmbeddingProvider` + `PgVectorStore`;
- in **tests / offline demo** — `FakeChatModel` + `HashingEmbeddingProvider` + `InMemoryVectorStore`.

`app.main.build_gateway()` picks the right components automatically: it uses the
live Qwen path when `openai` is importable and `DASHSCOPE_API_KEY` is set, and a
pgvector store when `psycopg2` + `DATABASE_URL` are usable — otherwise it falls
back to offline components so **the server and dashboard still run for a demo
with no key and no database** (or force it with `TOKENTRIM_OFFLINE=1`).

Because FastAPI is only a shell, the gateway's behaviour is tested *without*
HTTP in `tests/test_pipeline.py`. The HTTP tests in `tests/test_api.py` add
coverage when `fastapi` + `httpx` are installed and skip cleanly otherwise.

## The savings baseline (how the dashboard number is honest)

For each generated request the gateway records both the actual cost and a
**naive baseline**: the same request sent *uncompressed* to the flagship tier.
It measures the real compression ratio (uncompressed vs. compressed prompt
size) and scales the model's real input-token count by it, so the baseline
tracks the actual trimming done rather than a made-up multiplier. A cache hit
is credited with the flagship cost it avoided. `/stats` then reports total cost,
baseline, dollars saved, savings %, and cache hit rate.

## Running it

```bash
uvicorn app.main:app --reload           # live if DASHSCOPE_API_KEY is set, else offline
# or force offline for a no-network demo:
TOKENTRIM_OFFLINE=1 uvicorn app.main:app --reload
```

Then POST to `/chat` and open `http://localhost:8000/` for the dashboard:

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"query": "what are your opening hours"}'
```

## Verifying this phase

```bash
python -m unittest discover -s tests -t .
```

Expected: **53 tests, 3 skipped** (the HTTP tests skip without fastapi/httpx).
`test_pipeline.py` proves the full flow offline: first call generates, the
repeat is a free cache hit, simple routes to Flash, complex escalates to Max,
compression makes the baseline exceed the actual cost, and `/stats` aggregates
it all.

> **Offline caveat:** the local `HashingEmbeddingProvider` matches on shared
> tokens, so it catches exact/near-duplicate repeats but not word-disjoint
> paraphrases. The live `text-embedding-v4` path catches paraphrases too — that
> difference is the whole point of Layer 1, so demo the paraphrase case on the
> live path (see [Phase 4](PHASE_4_POLISH_AND_DEMO.md)).

---

**Previous:** [Phase 2 — Core Layers](PHASE_2_CORE_LAYERS.md) ·
**Next:** [Phase 4 — Polish & Demo](PHASE_4_POLISH_AND_DEMO.md).

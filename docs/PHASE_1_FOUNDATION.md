# Phase 1 — Foundation

> "Nothing clever yet, just plumbing that works." — the build guide

This phase establishes the skeleton every later phase builds on: a Model Studio
connection, a place for the pgvector cache to live, centralised configuration,
and a test harness that runs offline.

## What this phase delivers

| File | Purpose |
|---|---|
| `app/config.py` | Single source of truth for model IDs, the **pricing table**, routing thresholds, and the cache similarity cutoff. Env-overridable. |
| `scripts/hello_qwen.py` | Connectivity sanity check against Model Studio. |
| `db/schema.sql` | The `tokentrim_cache` table + pgvector IVFFlat index. |
| `.env.example` | Template for `DASHSCOPE_API_KEY`, `DATABASE_URL`, and optional overrides. |
| `requirements.txt` | Runtime dependencies (not needed for the unit tests). |
| `tests/test_config.py` | Verifies pricing covers all tiers, tiers are ordered cheap→flagship, and thresholds are sane. |

## Setup steps

1. **Model Studio account + key.** Activate Model Studio, pick the
   **Singapore (International)** region (it carries the 90-day free quota and
   the pricing used throughout), generate an API key, and put it in `.env`.
2. **Database.** Provision Postgres with the `pgvector` extension and run
   `psql "$DATABASE_URL" -f db/schema.sql`.
3. **Verify connectivity.** `python scripts/hello_qwen.py` should print a real
   model response.

## Design decisions

- **All tunables live in `config.py`.** When Alibaba changes prices — or a
  judge asks "what if the flagship gets cheaper?" — there is exactly one line
  to edit, and `config.validate()` guards against typo'd overrides.
- **`EMBED_DIM = 768`** keeps the pgvector index small and lookups cheap. It is
  duplicated in `db/schema.sql` (`VECTOR(768)`); change both together.
- **Tests are stdlib-only.** `config.validate()` returning `[]` is the first
  green check. No API key or database is required to run the suite.

## Verifying this phase

```bash
python -m unittest discover -s tests -t .
```

Expected: all tests pass. `python scripts/hello_qwen.py` additionally requires
a live key + the `openai` package, and is the manual end-to-end check.

## Sandbox / git note

A top-level `.git/` cannot be created in this sandbox, so the git database
lives in `.gitdb/`. See the README for the one-command normalisation
(`mv .gitdb .git`) to run outside the sandbox.

---

**Next:** [Phase 2 — Core Layers](PHASE_2_CORE_LAYERS.md).

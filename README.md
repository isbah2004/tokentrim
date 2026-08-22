# TokenTrim

A drop-in **token-optimization gateway** for Qwen-powered apps. It sits between
your app and Alibaba Cloud Model Studio and cuts token spend through three
layers, then shows the savings live in real dollars.

1. **Semantic cache** — skip generation entirely for repeated or *paraphrased* questions.
2. **Context compressor** — trim chat history and rerank RAG context before sending.
3. **Model router** — send each query to the cheapest model tier that can handle it.

> New here? Read [TokenTrim_Project_Explanation.md](TokenTrim_Project_Explanation.md)
> for the plain-language overview, or
> [TokenTrim_Hackathon_Build_Guide.md](TokenTrim_Hackathon_Build_Guide.md) for
> the original build guide this implementation follows.

---

## Project layout

```
token_optimizer/
├── app/
│   ├── config.py        # model IDs, pricing table, thresholds  (Phase 1)
│   ├── cache.py         # SemanticCache + in-memory store        (Phase 2)
│   ├── embeddings.py    # Qwen + offline embedding providers      (Phase 2)
│   ├── compressor.py    # history + RAG compression               (Phase 2)
│   ├── router.py        # difficulty scoring + model selection    (Phase 2)
│   ├── stats.py         # request logging + cost aggregation      (Phase 2)
│   ├── pipeline.py      # orchestrates the 3 layers               (Phase 3)
│   ├── qwen_client.py   # chat client wrapper + offline fake      (Phase 3)
│   └── main.py          # FastAPI /chat and /stats routes         (Phase 3)
├── static/dashboard.html      # Chart.js savings dashboard        (Phase 3)
├── scripts/                   # hello_qwen, batch index, demo, tuning, db_up
├── db/schema.sql              # pgvector table
├── docker-compose.yml         # pgvector Postgres (auto-loads schema)
├── tests/                     # unittest suite (stdlib only)
└── docs/                      # per-phase build notes
```

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add DASHSCOPE_API_KEY (DATABASE_URL is preset for Docker)
docker compose up -d --wait   # start pgvector Postgres; schema auto-loads on first boot
python scripts/hello_qwen.py  # sanity-check Model Studio connectivity
uvicorn app.main:app --reload # serve /chat, /stats, and the dashboard
```

## Database (Docker)

The semantic cache is backed by Postgres + [pgvector](https://github.com/pgvector/pgvector).
[`docker-compose.yml`](docker-compose.yml) runs it and applies
[`db/schema.sql`](db/schema.sql) automatically on first boot — no manual `psql`
step. `DATABASE_URL` in `.env` is already pointed at it.

```bash
./scripts/db_up.sh        # start + verify the extension and cache table exist
# or just:
docker compose up -d --wait
docker compose down       # stop (keeps data)
docker compose down -v    # stop and wipe data (schema re-applies on next up)
```

The schema init script only runs while the data volume is empty; to reapply an
edited `db/schema.sql`, `docker compose down -v` then `up` again. Without Docker,
the offline demo (`TOKENTRIM_OFFLINE=1`) needs no database at all.


## Running the tests

The core logic is pure Python and its tests need **no third-party packages**:

```bash
python -m unittest discover -s tests -t .
```

(They also run under `pytest` if you have it.)

---

## Documentation

The build is documented phase by phase. Each doc explains what that phase
delivers, the design decisions behind it, and how to verify it.

- [Phase 1 — Foundation](docs/PHASE_1_FOUNDATION.md) — config, pricing table, project skeleton.
- [Phase 2 — Core Layers](docs/PHASE_2_CORE_LAYERS.md) — cache, compressor, router, stats (each unit-tested in isolation).
- [Phase 3 — Gateway & Dashboard](docs/PHASE_3_GATEWAY_DASHBOARD.md) — the `Gateway`, FastAPI shell, and live Chart.js dashboard.
- [Phase 4 — Polish & Demo](docs/PHASE_4_POLISH_AND_DEMO.md) — threshold tuning, the pinned cost example, and the submission checklist.
- [Demo Script](docs/DEMO_SCRIPT.md) — the 6-beat judge walkthrough.

---

## A note on the git directory (`.gitdb`)

This repository was initialised inside a sandbox that forbids creating a
top-level `.git/`. The git database therefore lives in **`.gitdb/`**. Every
commit is a real, standard git commit — the directory just has a non-default
name. To turn this into a completely normal repository, run **once** from your
own terminal (outside the sandbox):

```bash
mv .gitdb .git
```

After that, `git status`, `git log`, remotes, etc. all work exactly as usual.
`.gitdb/` is listed in `.gitignore` so the git internals are never tracked.

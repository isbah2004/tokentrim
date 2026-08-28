# TokenTrim — Complete Execution Plan

> **Goal**: Take TokenTrim from its current state (functional MVP codebase) to a **hackathon-winning, demo-ready, investable product** for the Bano Qabil × Alibaba Cloud AI Hackathon 2026.

## Current State Assessment

### ✅ What's Already Built and Working

| Component | File(s) | Status |
|-----------|---------|--------|
| Config + pricing table | [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py) | ✅ Complete — 3 model tiers, pricing, thresholds, validation |
| Semantic cache (Layer 1) | [`cache.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py) | ✅ Complete — InMemory + PgVector stores, SemanticCache with threshold |
| Embeddings | [`embeddings.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py) | ✅ Complete — Qwen + offline Hashing providers |
| Context compressor (Layer 2) | [`compressor.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/compressor.py) | ✅ Complete — history trim + RAG reranking |
| Model router (Layer 3) | [`router.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py) | ✅ Complete — heuristic scoring, cost estimation, naive baseline |
| Gateway pipeline | [`pipeline.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/pipeline.py) | ✅ Complete — orchestrates all 3 layers |
| Chat model wrapper | [`qwen_client.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/qwen_client.py) | ✅ Complete — Qwen + Fake (offline) |
| FastAPI endpoints | [`main.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/main.py) | ✅ Complete — /chat, /stats routes |
| Stats logging | [`stats.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/stats.py) | ✅ Complete — JSONL logging + aggregation |
| Dashboard | [`dashboard.html`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/static/dashboard.html) | ✅ Basic Chart.js page |
| Database schema | [`schema.sql`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/db/schema.sql) | ✅ pgvector table + IVFFLAT index |
| Docker setup | [`docker-compose.yml`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docker-compose.yml) | ✅ pgvector/pg16 with auto-schema |
| Test suite | [`tests/`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/tests) | ✅ 57 tests (3 skipped) — all layers covered |
| Scripts | [`scripts/`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/scripts) | ✅ hello_qwen, simulate_demo, tune_threshold, batch_index, db_up, publish |
| Docs | 4 phase docs + demo script + build guide + project explanation + 31 research answers + 11 explanations | ✅ Exhaustive |

### ❌ What's NOT Done Yet — The Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| **No pitch deck** | Cannot present to judges | 🔴 Critical |
| **No demo video** (backup) | If internet fails, demo fails | 🔴 Critical |
| **Dashboard is basic** — minimal styling, no wow factor | Judges see a prototype, not a product | 🟡 High |
| **No live validation** — system never tested end-to-end with real Qwen API | Could fail on demo day | 🔴 Critical |
| **Cache threshold not tuned** with real embeddings | Judges ask "what if I phrase it differently?" — no data-backed answer | 🟡 High |
| **No CI/CD pipeline** | Missing professional polish | 🟢 Nice-to-have |
| **No README architecture diagram** (rendered) | README describes it but no visual | 🟡 High |
| **Routing thresholds not benchmark-validated** | "Where do 0.35 and 0.70 come from?" has no empirical answer | 🟢 Nice-to-have |
| **No model escalation** (v2 stretch) | Not blocking for MVP | ⚪ Stretch |
| **Submission format unconfirmed** | Could miss deadline requirements | 🔴 Critical |

---

## Execution Plan — 5 Phases

> [!IMPORTANT]
> **The hackathon deadline is the hard constraint.** Confirm exact submission format and deadline with Bano Qabil coordinators BEFORE starting Phase 3. Everything below is ordered by impact-to-effort ratio.

---

### Phase A: Live Validation (Day 1 — ~3 hours)

**Goal**: Prove the entire system works end-to-end with real Alibaba Cloud APIs. Every minute spent here prevents a catastrophic demo-day failure.

#### A1. Environment Setup
- [ ] Verify `DASHSCOPE_API_KEY` is valid and has quota
- [ ] `cp .env.example .env` and fill in real credentials
- [ ] `python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r requirements.txt`
- [ ] Run `python scripts/hello_qwen.py` — confirm a real Qwen response

#### A2. Database Setup
- [ ] `docker compose up -d --wait` — start pgvector Postgres
- [ ] `./scripts/db_up.sh` — verify schema + vector extension
- [ ] `docker compose exec db psql -U tokentrim -d tokentrim -c "SELECT count(*) FROM tokentrim_cache;"` — confirm table exists

#### A3. Live Gateway Test
- [ ] `uvicorn app.main:app --reload`
- [ ] Send a fresh query via curl:
  ```bash
  curl -s localhost:8000/chat -H 'content-type: application/json' \
    -d '{"query": "what are your opening hours"}' | python -m json.tool
  ```
- [ ] Verify: `cached: false`, real model name, real token counts, real cost
- [ ] Send the same query again — verify: `cached: true`, cost = 0
- [ ] Send a paraphrase ("when are you open") — verify: semantic cache hit
- [ ] Send a hard query ("Compare and analyze three approaches to microservice architecture") — verify: routes to `qwen3.7-max`
- [ ] Open `http://localhost:8000/` — verify dashboard shows live data
- [ ] Hit `/stats` — verify JSON summary is accurate

#### A4. Run Tests Against Live
- [ ] `python -m unittest discover -s tests -t .` — all 57 tests pass, 3 skipped
- [ ] With API key set: run the 3 skipped tests manually (if they exist) to validate live integration

> [!CAUTION]
> **If any step in Phase A fails, STOP and fix it before proceeding.** Nothing else matters if the core pipeline doesn't work live.

---

### Phase B: Cache Threshold Tuning (Day 1 — ~1.5 hours)

**Goal**: Have a data-backed answer to "What if I phrase it differently?" — the question every judge will ask.

#### B1. Run Threshold Tuner (Live)
- [ ] Ensure `DASHSCOPE_API_KEY` is set
- [ ] `python scripts/tune_threshold.py`
- [ ] Record the suggested threshold value
- [ ] Compare against the current `0.92` default

#### B2. Expand Paraphrase Pairs
- [ ] Add 5–10 more paraphrase pairs relevant to your demo domain:
  ```python
  # Example pairs to add to tune_threshold.py
  ("What services do you offer?", "What can you do for me?"),
  ("How much does it cost?", "What are your prices?"),
  ("Can I get a refund?", "What is your refund policy?"),
  ```
- [ ] Add 5–10 distractor pairs (semantically different):
  ```python
  ("What are your hours?", "What color is your logo?"),
  ("How much does it cost?", "Where is your office located?"),
  ```
- [ ] Re-run `tune_threshold.py` and note the separation between paraphrase and distractor similarity scores

#### B3. Set Final Threshold
- [ ] Update `CACHE_SIMILARITY_THRESHOLD` in `.env` (or `config.py`) to the tuned value
- [ ] Re-run the live gateway test from A3 to confirm cache hits still work correctly
- [ ] **Document the result**: "We tested X pairs. Paraphrase similarities ranged from Y to Z. Distractor similarities ranged from A to B. Threshold set to C."

---

### Phase C: Dashboard & Visual Polish (Day 2 — ~4 hours)

**Goal**: Transform the dashboard from a developer tool into something that makes judges say "this looks like a product."

#### C1. Dashboard Upgrade

Redesign [`static/dashboard.html`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/static/dashboard.html) with:

- [ ] **Dark theme** with a modern color palette (deep navy background, accent gradients)
- [ ] **Hero metrics bar** at the top: Total Savings ($), Requests Handled, Cache Hit Rate (%), Avg Latency
- [ ] **Before vs. After cost chart** — the central visual. Side-by-side bars showing naive cost vs. actual cost per request
- [ ] **Model distribution pie chart** — what % of queries went to Flash/Plus/Max
- [ ] **Cache hit rate line chart** — shows the hit rate growing over time
- [ ] **Live request log** — last 10 requests with model, cost, cached status, latency
- [ ] **Auto-refresh** every 3 seconds (already fetching `/stats`)
- [ ] **Responsive layout** — looks good on both projector (wide) and laptop
- [ ] **TokenTrim branding** — logo/name at the top, "Powered by Alibaba Cloud" badge
- [ ] **Micro-animations** — counters that tick up, charts that animate on data change

#### C2. API Enhancements for Dashboard

The current `/stats` endpoint may need richer data for the new dashboard:

- [ ] Add per-request history to `/stats` (last N requests with details)
- [ ] Add model distribution breakdown (count per model tier)
- [ ] Add time-series data (cost over time, not just totals)

#### C3. Architecture Diagram

- [ ] Create a clean, professional architecture diagram (Mermaid or generated image) for the README and pitch deck
- [ ] Show the 3-layer pipeline with the Qwen model tiers
- [ ] Include the dashboard as the output

---

### Phase D: Pitch Deck & Demo Prep (Day 2–3 — ~4 hours)

**Goal**: Build a 6–8 slide pitch deck and rehearse the demo until it's flawless.

#### D1. Pitch Deck Structure

| Slide # | Title | Content |
|---------|-------|---------|
| 1 | **The Problem** | "AI apps waste 50–90% of their token budget. Three habits: replayed history, over-stuffed context, one-model-fits-all." |
| 2 | **The Solution** | "TokenTrim: a drop-in gateway that sits between your app and Qwen. Three layers: Semantic Cache, Context Compressor, Model Router." |
| 3 | **Architecture** | Clean diagram of the 3-layer pipeline. Call out: "Not the same as prefix cache — catches paraphrases." |
| 4 | **Live Demo** | Screenshots of dashboard + live numbers. Or switch to the live demo here. |
| 5 | **The Numbers** | Worked example: 8,200 → 3,100 tokens. $0.00364 → $0.00043/call. **88.2% cost reduction.** At 50K req/day: $5,460/mo → $645/mo. |
| 6 | **Why Qwen?** | "Built specifically for Alibaba's ecosystem. Uses text-embedding-v4, Qwen Flash/Plus/Max tiers. Prices verified against live Model Studio pricing." |
| 7 | **Business Model** | "Metered SaaS fee on top of token savings. Pays for itself Day 1. Drop-in proxy — one-line URL change to adopt." |
| 8 | **The Team & Ask** | Team intro, GitHub repo, what you'd build next (LLM classifier, streaming, multi-tenant). |

#### D2. Demo Rehearsal

Follow the 6-beat script from [`DEMO_SCRIPT.md`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/DEMO_SCRIPT.md):

- [ ] Rehearsal 1: Run through with live API. Time it (target: 4–5 minutes).
- [ ] Rehearsal 2: Practice transitions between terminal and dashboard.
- [ ] Rehearsal 3: Practice the offline fallback (`TOKENTRIM_OFFLINE=1`).
- [ ] Prepare answers for likely judge questions:
  - "What if the cache returns a wrong answer?" → Threshold tuning data from Phase B
  - "Why these threshold values?" → Heuristic + benchmark methodology from research answers
  - "How is this different from prefix cache?" → Paraphrase detection — the key differentiator
  - "What happens if the API is down?" → Seamless offline fallback
  - "Is this unique?" → Combination of 4 techniques in one pipeline is unique; individual pieces exist

#### D3. Demo Video (Backup)

- [ ] Screen-record the full live demo (5 minutes)
  - Show the 3 curl commands
  - Show the paraphrase cache hit (THE key moment)
  - Show the dashboard updating in real time
  - Show the hard query routing to Max
- [ ] Save the video in a shareable format (MP4, uploaded to Google Drive or YouTube)

> [!WARNING]
> **The demo video is NOT optional.** Venue Wi-Fi can and will fail. The video is your insurance policy.

---

### Phase E: Final Polish & Submission (Day 3 — ~3 hours)

**Goal**: Cross every T, dot every I. Submit with confidence.

#### E1. Code Quality

- [ ] Run full test suite one final time: `python -m unittest discover -s tests -t .`
- [ ] Verify the pinned cost example test: `python -m unittest tests.test_cost_example`
- [ ] Re-verify pricing against [Alibaba's live pricing page](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [ ] Clean up any debug prints or TODO comments

#### E2. README Final Pass

- [ ] Ensure the architecture diagram is embedded
- [ ] Quickstart instructions are copy-paste-able
- [ ] Link to the pitch deck and demo video
- [ ] Add a "Results" section with the key metrics from your live testing

#### E3. Git & Repository

- [ ] Clean git history: `mv .gitdb .git` (if not already done)
- [ ] `git add -A && git commit -m "Hackathon submission"`
- [ ] Push to GitHub: `./scripts/publish.sh`
- [ ] Verify the repo is accessible (private → share with organizers, or make public)

#### E4. Submission

- [ ] **Confirm exact submission format** with Bano Qabil coordinators
- [ ] Submit: repo link + pitch deck + demo video
- [ ] Double-check deadline timezone

---

## Submission Checklist

| Item | Status |
|------|--------|
| Working repo with clear README | ✅ Built |
| Three layers working independently (unit-tested) | ✅ 57 tests |
| Dashboard showing live-computed savings | ⬜ Needs upgrade (Phase C) |
| Worked cost example pinned to a test | ✅ `test_cost_example.py` |
| Short pitch deck | ⬜ Phase D |
| Demo video (backup) | ⬜ Phase D |
| Confirmed submission format/deadline | ⬜ Phase E |

---

## Stretch Goals (Only If Time Remains After Phase E)

In priority order:

| Goal | Effort | Impact | How |
|------|--------|--------|-----|
| **LLM-based difficulty classifier** | ~3h | High | Replace heuristic scorer with a single `qwen3.5-flash` call that returns "simple/medium/complex" |
| **Model-agnostic tier system** | ~2h | Medium | Refactor `config.py` to use a sorted list of model tiers instead of three hardcoded constants |
| **Streaming responses** | ~3h | Medium | Pass through SSE events while still counting tokens |
| **Cross-encoder RAG reranking** | ~2h | Medium | Better relevance ordering than cosine similarity |
| **Drop-in proxy mode** | ~4h | High | One-line `base_url` change for existing Qwen apps |
| **CI/CD via GitHub Actions** | ~1h | Low | Auto-run tests on push |
| **TTL-based cache expiration** | ~1h | Low | Add `expires_at` column and check during lookup |

---

## Timeline Summary

```
Day 1 (Morning)  │  Phase A: Live Validation (~3h)
                  │  → System works end-to-end with real Qwen API
                  │
Day 1 (Afternoon) │  Phase B: Cache Threshold Tuning (~1.5h)
                  │  → Data-backed answer to "what if I rephrase?"
                  │
Day 2 (Morning)   │  Phase C: Dashboard & Visual Polish (~4h)
                  │  → Product-quality dashboard that wows judges
                  │
Day 2 (Afternoon) │  Phase D: Pitch Deck & Demo Prep (~4h)
                  │  → 8-slide deck, rehearsed demo, backup video
                  │
Day 3 (Morning)   │  Phase E: Final Polish & Submission (~3h)
                  │  → Tests pass, repo clean, submitted
                  │
Day 3 (Afternoon) │  Stretch Goals (if time permits)
                  │  → LLM classifier, streaming, proxy mode
```

> [!TIP]
> **The single most important thing**: The live demo with the paraphrase cache hit. If judges see "when are you open" match a cached answer from "what are your hours" — and the dashboard shows $0.00 cost — you've already won half the argument. Everything else is supporting evidence.

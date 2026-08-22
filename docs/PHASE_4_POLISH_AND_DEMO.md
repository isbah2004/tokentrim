# Phase 4 — Polish & Demo

The three layers work and the dashboard is live. This phase makes the build
*defensible in front of judges*: tune the one number they'll poke at, pin the
headline cost claim to a test so it can't drift, script the demo, and check off
what a submission needs.

## What this phase delivers

| File | Purpose |
|---|---|
| `scripts/tune_threshold.py` | Measure the cache similarity threshold against labelled paraphrase/distractor pairs instead of guessing. |
| `scripts/simulate_demo.py` | Drive the offline gateway through a realistic traffic mix to populate the dashboard with real numbers. |
| `tests/test_cost_example.py` | Pins the build guide's headline worked example to the pricing in `config` so the claim can't silently drift. |
| `docs/DEMO_SCRIPT.md` | The 6-beat judge walkthrough, ready to rehearse. |

## Tuning the cache threshold (the question judges will ask)

The single easiest thing to challenge is *"what if I phrase it slightly
differently?"* — so measure it rather than assert it:

```bash
python scripts/tune_threshold.py
```

It embeds labelled question pairs — paraphrases that *should* share a cached
answer, distractors that should *not* — prints the cosine similarity of each,
and suggests a threshold that separates the two classes. Move
`CACHE_SIMILARITY_THRESHOLD` in [`app/config.py`](../app/config.py) toward the
suggested value.

> **Run this on the live path.** With `openai` + `DASHSCOPE_API_KEY` set it uses
> `text-embedding-v4`, which places paraphrases well above distractors and gives
> a clean threshold. The offline `HashingEmbeddingProvider` matches on shared
> tokens, so word-disjoint paraphrases ("when are you open" vs. "what are your
> opening hours") collapse toward zero and the classes overlap — the script says
> so explicitly rather than suggesting a bogus number. Semantic paraphrase
> matching is the whole point of Layer 1, so it must be demoed live.

The default `0.92` is deliberately conservative: a wrong cache hit (serving a
stale answer to a genuinely different question) is far more damaging in a demo
than a miss, so bias toward precision and let borderline cases fall through to
generation.

## Populating the dashboard for a demo

A dashboard of zeros doesn't sell. Seed it with a realistic mix — repeated FAQs
that become cache hits, simple questions that route to Flash, and a couple of
genuinely hard ones that escalate to Max:

```bash
python scripts/simulate_demo.py --reset     # clear, then replay the scripted traffic
uvicorn app.main:app --reload               # open http://localhost:8000/
```

This runs fully offline against the fakes, so it works with no key and no
database — useful for practising the walkthrough and for screenshots. On demo
day, drive the *live* gateway with real queries instead so the numbers are
genuinely live-computed (see the checklist below).

## The worked cost example, pinned to a test

The headline claim — **~88% cost reduction per call** — is not a slide, it's a
test. [`tests/test_cost_example.py`](../tests/test_cost_example.py) recomputes it
from the pricing in `config`:

| | Model | Input tok | Output tok | Cost/call |
|---|---|---:|---:|---:|
| **Before** (full prompt, flagship-by-default) | `qwen-plus` | 8,200 | 300 | ~$0.00364 |
| **After** (compressed + routed) | `qwen3.5-flash` | 3,100 | 300 | ~$0.00043 |

That's an **88.2%** reduction per call. At 50k requests/day that's roughly
**$5,460/mo → $645/mo**. If a judge opens Alibaba's pricing page mid-demo, these
numbers reconcile — and if anyone edits the pricing table in `config`, the test
fails loudly instead of the pitch quietly going stale.

## Demo script for judges

The full 6-beat walkthrough lives in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md). The
spine: **lead with the problem**, then three live queries — a fresh miss, a
paraphrased cache hit (the moment that separates this from "just use the prefix
cache"), and a genuinely hard query that the router escalates to `qwen3.7-max`
to prove it isn't just "always pick cheap" — then the **live dashboard**, then
the **business case** (a metered layer on top of token savings).

## Submission checklist

Mapped to the build guide's Section 13, with current status:

- [x] Working repo with a clear README (architecture, setup, how to run the demo) — [`README.md`](../README.md)
- [x] The three layers demonstrably working *independently*, not just one happy path — unit-tested per layer in [`tests/`](../tests)
- [x] Dashboard computes savings live from real request logs — not a static screenshot with invented numbers
- [x] Worked cost example reconciled against real pricing — [`tests/test_cost_example.py`](../tests/test_cost_example.py)
- [ ] Short pitch deck: problem → architecture → live numbers → business case *(prepare from `DEMO_SCRIPT.md` + dashboard screenshots)*
- [ ] Demo video as backup in case live API access is flaky on the day
- [ ] **Confirm exact submission format + deadline with the Bano Qabil / Alibaba Cloud coordinators** — post-selection instructions are communicated directly to shortlisted teams, so treat this repo as the build, not the submission spec.

## Verifying this phase

```bash
python -m unittest discover -s tests -t .
```

Expected: **57 tests, 3 skipped** (the HTTP tests in `test_api.py` skip without
fastapi/httpx). The four new tests are the pinned cost example.

## Stretch goals (if time remains)

From the guide's Section 12, in rough effort-to-impact order: an LLM-based
difficulty classifier (one cheap Flash call) to replace the router heuristic;
cross-encoder reranking for RAG chunks; an explicit context cache for large
reused documents; per-tenant dashboards; streaming responses with token
accounting intact; and a drop-in proxy mode so an existing Qwen app adopts
TokenTrim with a one-line base-URL change.

---

**Previous:** [Phase 3 — Gateway & Dashboard](PHASE_3_GATEWAY_DASHBOARD.md) ·
**Back to:** [README](../README.md).

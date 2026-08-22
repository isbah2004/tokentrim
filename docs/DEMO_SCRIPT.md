# Demo Script — TokenTrim (for judges)

A 6-beat walkthrough, ~4–5 minutes. Rehearse it against the **live** gateway
(`DASHSCOPE_API_KEY` set) so the paraphrase cache hit and the dollar figures are
real. Keep the dashboard open in a second tab the whole time.

**Before you start:** seed a little history so the dashboard isn't empty, then
clear it right before the live run so judges watch the numbers move from a clean
slate — or leave the seed in and narrate over it. Your call; decide in rehearsal.

```bash
# terminal 1 — the gateway (live)
uvicorn app.main:app --reload
# terminal 2 — you'll paste the curl calls below here
```

---

### 1. Open with the problem, not the tech

> "Most Qwen-powered apps burn tokens on things that don't need to be there —
> the full chat history replayed every turn, RAG context that's mostly
> irrelevant, and defaulting to the flagship model for questions a cheap tier
> would nail. TokenTrim is a gateway that sits in front of Model Studio and
> removes that waste before the request ever costs you anything."

Don't show code yet. Sell the leak first.

### 2. Live query #1 — a fresh, non-cached question

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"query": "what are your opening hours"}' | jq
```

Call out on screen: `cached: false`, which model it routed to, the input token
count, the cost. This is the baseline — a normal request flowing through.

### 3. Live query #2 — a paraphrase of #1 (the key beat)

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"query": "when are you open"}' | jq
```

Different words, same meaning. Point at `cached: true` and the near-zero cost.

> "This is the semantic cache. It's not string matching and it's not the
> provider's prefix cache — those only catch identical prefixes. This caught a
> completely different phrasing because it matches on *meaning*. That's the
> difference between 'reuse the same prompt' and 'reuse the same *question*.'"

**Don't rush this one.** It's what separates TokenTrim from "just turn on the
prefix cache."

### 4. Live query #3 — something genuinely hard

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"query": "Compare your enterprise and pro plans and recommend one for a 200-person company migrating from a competitor, with reasoning."}' | jq
```

Point at the router escalating to `qwen3.7-max`.

> "It didn't cheap out. The router scored this as hard and sent it to the
> flagship. TokenTrim isn't 'always pick the cheap model' — it's 'pick the
> *right* model,' which is what makes the savings safe to turn on in
> production."

### 5. Show the dashboard

Switch to `http://localhost:8000/`. Walk across it:

- **Cumulative tokens saved** and **real dollars saved** — computed live from the
  three requests they just watched, not a static number.
- **Cache hit rate** — climbs the moment query #2 hit.
- **Naive vs. actual cost** bars — the gap *is* the product.

> "Every number here was computed from the requests you just saw. The baseline is
> the same traffic sent uncompressed to the flagship — the honest 'what you'd pay
> without us.'"

### 6. Close with the business case

> "This isn't a hackathon toy. It's a metered layer — a small fee on top of the
> tokens we save, or a flat SaaS tier. It pays for itself on the first day of
> real traffic, and it's exactly the kind of investable infrastructure play this
> hackathon is scouting for."

---

## Backup plan (if live API is flaky on the day)

The whole demo runs offline against the local fakes — no key, no database:

```bash
python scripts/simulate_demo.py --reset
TOKENTRIM_OFFLINE=1 uvicorn app.main:app --reload
```

Caveat to say out loud if you fall back: the offline embedder matches on shared
words, so it catches exact repeats but **not** the paraphrase in beat #3 — that
one needs the live `text-embedding-v4`. Have a **recorded video** of the live
paraphrase hit as the real backup; the offline mode is for proving the pipeline
and dashboard still run, not the paraphrase claim.

---

**See also:** [Phase 4 — Polish & Demo](PHASE_4_POLISH_AND_DEMO.md).

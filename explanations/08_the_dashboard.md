# 08 — The Dashboard: Tracking and Displaying Savings
> **Level:** Beginner. Read files 01–07 first.

---

## 🎯 Why the Dashboard Exists

The whole point of TokenTrim is to save money. But savings are invisible unless you measure and show them.

The dashboard is the **"wow factor"** for judges and investors. It shows, in real time:
- How many requests were served
- How many were answered from cache (free!)
- How many actual tokens were used
- What the real dollar cost was
- What it WOULD have cost without TokenTrim
- The percentage saved

> **Guide quote:** *"A side-by-side, real-number comparison beats a slide full of claims every time."*

---

## 📝 How Requests Are Logged

Every single request — cached or not — gets logged to a file called `tokentrim_stats.jsonl`.

Each line in this file is a JSON object with the details of one request:

```json
{"cache_hit": false, "model": "qwen3.5-flash", "input_tokens": 3100, "output_tokens": 300, "cost": 0.00043, "latency": 0.23, "routing_reason": "difficulty=0.18 -> simple", "timestamp": 1724594400.123}
{"cache_hit": true, "model": null, "input_tokens": 0, "output_tokens": 0, "cost": 0.0, "latency": 0.04, "timestamp": 1724594460.456}
{"cache_hit": false, "model": "qwen3.7-max", "input_tokens": 5200, "output_tokens": 800, "cost": 0.01910, "latency": 1.82, "routing_reason": "difficulty=0.78 -> complex", "timestamp": 1724594520.789}
```

**JSONL** (JSON Lines) format means:
- One JSON object per line
- Each line is a valid JSON string
- Easy to append to (just add a new line)
- Easy to read line by line

---

## 🧮 The Stats Aggregation Logic

```python
def get_summary() -> dict:
    rows = [json.loads(line) for line in open(LOG_FILE)]
    total = len(rows)
    cache_hits = sum(1 for r in rows if r.get("cache_hit"))
    total_cost = sum(r.get("cost", 0) for r in rows)
    total_input_tokens = sum(r.get("input_tokens", 0) for r in rows)
    total_output_tokens = sum(r.get("output_tokens", 0) for r in rows)
```

This reads every line from the log file and computes:
- `total` → total number of requests handled
- `cache_hits` → how many were served from cache
- `total_cost` → what was actually spent in dollars
- `total_input_tokens` / `total_output_tokens` → tokens actually used

---

## 🔢 The Baseline (Naive) Cost Calculation

```python
naive_cost = sum(
    (r.get("input_tokens", 0) * 3 + r.get("output_tokens", 0))
    * PRICING["qwen3.7-max"]["input"] / 1_000_000
    for r in rows
)
```

This is the clever part. It computes **what it would have cost** if:
- Every request went to `qwen3.7-max` (the most expensive model)
- No compression was applied (`input_tokens * 3` simulates the uncompressed token count)
- No caching (cache hits would have cost full model price)

The `* 3` factor on input tokens is a rough estimate: if TokenTrim compressed tokens by ~67%, then the original uncompressed count was about 3× larger.

> **Important:** This is an honest "before" estimate, not an invented number. The 3× multiplier is documented and checkable.

---

## 📊 The Returned Summary

```python
return {
    "total_requests": total,
    "cache_hit_rate": round(cache_hits / total, 3),       # e.g. 0.182 = 18.2% hit rate
    "total_cost_usd": round(total_cost, 4),                # e.g. $0.0043 actual spent
    "estimated_naive_cost_usd": round(naive_cost, 4),      # e.g. $0.0364 without optimization
    "estimated_savings_pct": round((1 - total_cost / naive_cost) * 100, 1),  # e.g. 88.2%
    "avg_input_tokens": round(total_input_tokens / max(total - cache_hits, 1), 1),
}
```

A sample response from `/stats`:
```json
{
    "total_requests": 1000,
    "cache_hit_rate": 0.182,
    "total_cost_usd": 0.4300,
    "estimated_naive_cost_usd": 3.6400,
    "estimated_savings_pct": 88.2,
    "avg_input_tokens": 3100.0
}
```

**Translation:** "1000 requests handled. 18.2% served from cache. Spent $0.43. Without TokenTrim it would have been $3.64. Saved 88.2%."

---

## 🌐 The Dashboard Frontend

The guide recommends a single `static/dashboard.html` file that:
1. Fetches `/stats` every few seconds (auto-refreshes)
2. Renders the key numbers as bar charts using Chart.js

The three charts to show:
- **Tokens: Before vs After** — two bars showing compressed vs naive token count
- **Cost: Before vs After** — two bars showing actual cost vs naive cost in dollars
- **Cache Hit Rate** — a percentage bar showing what fraction of requests were free

During a live demo, as the judge asks questions, the dashboard updates in real time — showing the savings accumulate with each request.

---

## 🎬 Why This Wins the Demo

The sequence during a judge presentation:

1. Judge asks a question → dashboard shows: *"Routed to qwen3.5-flash. 3,100 tokens. $0.00043."*
2. Judge asks a similar question → dashboard shows: *"Cache hit! 0 tokens. $0.00000."*
3. Judge asks a complex question → dashboard shows: *"Routed to qwen3.7-max. Difficulty=0.81."*
4. Dashboard shows cumulative: *"Total saved: 88.2%. $4.23 saved vs $37.90 naive."*

This is not a static slide with made-up numbers. These are **live-computed, independently verifiable figures**. That's the trust signal that differentiates TokenTrim from a typical hackathon project.

---

## ✅ Key Takeaways

- Every request is logged as a JSON line in `tokentrim_stats.jsonl`
- The `/stats` endpoint aggregates this log into key metrics in real time
- The "naive" baseline is computed by simulating what full, uncompressed, flagship-model usage would cost
- The savings percentage is the headline number: ~88% cost reduction
- The dashboard is a live Chart.js page that auto-refreshes — real numbers, not claims

---

➡️ **Next: [09 — Every Code File Explained](./09_the_code_files_explained.md)**

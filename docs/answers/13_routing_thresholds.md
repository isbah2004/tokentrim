# 13. Routing Thresholds

## The Current Thresholds

From [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L57-L58):

```python
ROUTER_SIMPLE_MAX = 0.35   # Score < 0.35 → Flash
ROUTER_MEDIUM_MAX = 0.70   # 0.35 ≤ Score < 0.70 → Plus
                           # Score ≥ 0.70 → Max
```

## Where Do These Numbers Come From?

These are **heuristic starting points**, not empirically derived values. They were chosen based on the following reasoning:

### The Scoring Function

The [`score_difficulty()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L33-L46) function produces a score in `[0, 1]`:

```
score  = min(word_count / 40, 1.0) × 0.4     # up to 0.4
       + min(rag_chunk_count / 5, 1.0) × 0.3 # up to 0.3
       + min(history_len / 10, 1.0) × 0.1    # up to 0.1
       + (0.2 if complexity keyword found)    # up to 0.2
       ─────────────────────────────────────
       Maximum possible: 1.0
```

### Why 0.35?

A query that scores below 0.35 is likely:
- Short (< 14 words, contributing < 0.14)
- Has no RAG context (contributing 0)
- Has no history (contributing 0)
- Has no complexity keywords (contributing 0)

**Example**: `"What time is it?"` → 5 words → `(5/40) × 0.4 = 0.05` → **Flash**

This is the kind of trivial query that any model can handle. Sending it to the flagship model would waste 25× the cost.

### Why 0.70?

A query that scores 0.70+ likely has:
- Moderate-to-long text (20+ words → 0.20+)
- Some RAG context (2+ chunks → 0.12+)
- Some history (a few turns → 0.03+)
- A complexity keyword like "analyze" (+0.20)

**Example**: `"Analyze and compare the performance of these two algorithms"` with 3 RAG chunks and 5 history turns:
```
(10/40) × 0.4 = 0.10   # word count
(3/5) × 0.3  = 0.18    # RAG chunks
(5/10) × 0.1 = 0.05    # history
+ 0.20                   # "analyze" keyword
= 0.53 → Plus (not quite Max)
```

To reach Max, the query would need to be longer, have more RAG context, or combine multiple complexity signals.

## Should These Be Arbitrary?

**No.** The thresholds should ultimately be derived from data, not intuition. The process should be:

1. **Create a benchmark dataset** (see [Question 16](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/16_determining_routing_values.md)) with queries of known difficulty.
2. **Test each query** against Flash, Plus, and Max.
3. **Measure accuracy** — Can Flash handle this correctly? Does it need Plus? Does it need Max?
4. **Find the boundary** — The threshold should be the score at which Flash starts failing and Plus is needed.

## What the Thresholds Should Be Based On

| Factor | How It Influences Thresholds |
|--------|------------------------------|
| **Benchmark accuracy** | If Flash handles 95% of queries scoring < 0.40 correctly, the threshold might move from 0.35 to 0.40 |
| **Cost efficiency** | Higher thresholds for Flash → more savings, but risk of quality degradation |
| **Latency** | Flash is faster; if latency matters, prefer Flash for more queries |
| **Token usage** | Complex queries use more tokens; routing to Max for complex queries avoids retries |
| **Failure rate** | If Flash fails on 20% of queries in the 0.30–0.40 range, the threshold should be lower |
| **Historical data** | Real production traffic reveals the actual distribution of query difficulties |

## The Pragmatic Approach for the Hackathon

For the MVP:
1. **Keep 0.35 and 0.70 as defaults** — They are reasonable starting points.
2. **Make them configurable** — They are already environment-variable overridable via `TOKENTRIM_ROUTER_SIMPLE_MAX` and `TOKENTRIM_ROUTER_MEDIUM_MAX`.
3. **Log every routing decision** — The stats log captures `routing_reason`, which includes the difficulty score.
4. **After the demo, analyze the logs** — Adjust thresholds based on real data.

The current approach is honest: the thresholds are heuristic, documented, configurable, and the system is designed to evolve them based on empirical evidence.

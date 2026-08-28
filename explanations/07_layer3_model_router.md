# 07 — Layer 3: The Model Router
> **Level:** Beginner–Intermediate. Read files 01–06 first.

---

## 🎯 One-Line Summary

After compressing the prompt, decide which Qwen model should answer it — based on how difficult the question actually is — so you're not paying flagship-model prices for simple questions.

---

## 🎭 The Core Metaphor

Imagine a hospital triage system:
- A patient with a minor cut → goes to the nurse (fast, cheap)
- A patient with a broken leg → goes to a junior doctor (moderate)
- A patient with a complex surgery → goes to the specialist surgeon (expensive)

You don't send every patient to the surgeon. TokenTrim's model router is the triage system for AI requests.

---

## 💰 The Price Difference Matters Enormously

```
qwen3.5-flash: $0.10 input / $0.40 output per 1M tokens
qwen-plus:     $0.40 input / $1.20 output per 1M tokens  (4× more expensive)
qwen3.7-max:   $2.50 input / $7.50 output per 1M tokens  (25× more expensive than flash)
```

If you route just 50% of requests to `qwen3.5-flash` instead of `qwen-plus`, you cut costs on those requests by 75%. That's significant at scale.

---

## 📐 How Difficulty is Scored (The Heuristic)

The guide deliberately uses a **heuristic** (rule-based) scorer instead of an AI-based classifier.

**Why heuristics?**
> Using another AI call to classify the question would itself cost tokens, add latency, and could fail. A simple rule-based scorer costs zero tokens, is instant, and never crashes.

The scorer returns a number between **0.0** (trivially simple) and **1.0** (highly complex):

```python
def score_difficulty(query: str, rag_chunk_count: int, history_len: int) -> float:
    score = 0.0
    word_count = len(query.split())
    
    score += min(word_count / 40, 1.0) * 0.4   # word count (up to 40% of score)
    score += min(rag_chunk_count / 5, 1.0) * 0.3 # RAG chunks (up to 30%)
    score += min(history_len / 10, 1.0) * 0.1    # conversation depth (up to 10%)
    
    hard_signals = ["compare", "analyze", "why", "explain step by step", "design", "debug"]
    if any(sig in query.lower() for sig in hard_signals):
        score += 0.2  # hard keywords add 20%
    
    return min(score, 1.0)  # cap at 1.0
```

Let's trace through some examples:

### Example 1: "Hi, what's your name?"
- Word count: 5 words → `(5/40) × 0.4 = 0.05`
- RAG chunks: 0 → `0 × 0.3 = 0`
- History: 0 turns → `0 × 0.1 = 0`
- Hard signals: none → `+0`
- **Total score: 0.05** → `qwen3.5-flash` (cheap tier)

### Example 2: "What's the price of Product X and how does it compare with Product Y?"
- Word count: 18 words → `(18/40) × 0.4 = 0.18`
- RAG chunks: 3 → `(3/5) × 0.3 = 0.18`
- History: 4 turns → `(4/10) × 0.1 = 0.04`
- Hard signals: "compare" → `+0.20`
- **Total score: 0.60** → `qwen-plus` (mid tier)

### Example 3: "Analyze this code and debug the memory leak step by step"
- Word count: 11 words → `(11/40) × 0.4 = 0.11`
- RAG chunks: 5 → `(5/5) × 0.3 = 0.30`
- History: 8 turns → `(8/10) × 0.1 = 0.08`
- Hard signals: "analyze", "debug", "step by step" → `+0.20`
- **Total score: 0.69** → just under `qwen3.7-max` — would go to `qwen-plus`

*(Adjust thresholds based on your real data)*

---

## 🗺️ The Routing Decision

```python
def pick_model(query: str, rag_chunk_count: int, history_len: int) -> RoutingDecision:
    score = score_difficulty(query, rag_chunk_count, history_len)
    if score < 0.35:
        return RoutingDecision("qwen3.5-flash", f"difficulty={score:.2f} -> simple")
    elif score < 0.7:
        return RoutingDecision("qwen-plus", f"difficulty={score:.2f} -> medium")
    else:
        return RoutingDecision("qwen3.7-max", f"difficulty={score:.2f} -> complex")
```

```
Score 0.00 ──────── 0.35 ──────── 0.70 ──────── 1.00
            Flash        Plus           Max
            (cheap)    (balanced)    (expensive)
```

The `RoutingDecision` dataclass stores:
- `model`: which model to use (e.g., `"qwen3.5-flash"`)
- `reason`: a human-readable explanation (e.g., `"difficulty=0.12 -> simple"`)

The reason is logged and shown on the dashboard — so you can always see WHY a specific model was chosen.

---

## 💵 Cost Estimation

```python
PRICING = {
    "qwen3.5-flash": {"input": 0.10, "output": 0.40},
    "qwen-plus":     {"input": 0.40, "output": 1.20},
    "qwen3.7-max":   {"input": 2.50, "output": 7.50},
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
```

After the API call returns, we know the exact token counts. This function computes the exact dollar cost of that specific request. This number gets logged and aggregated on the dashboard.

---

## 🎓 Why Heuristics Are Enough for the MVP

The guide is transparent about this: the heuristic scorer isn't perfect. It might occasionally:
- Route a genuinely complex question to `qwen-plus` instead of `qwen3.7-max`
- Route a technically-worded but simple question to a more expensive model

But for the hackathon demo, "good enough" routing is a huge improvement over "always use the most expensive model". The upgrade path (using a cheap `qwen3.5-flash` classifier) is clearly described in Section 12 of the build guide — which is a legitimate talking point for investor Q&A:

> *"We know how to improve the classifier — we intentionally kept it simple for the MVP because it's zero-cost and has no failure modes. Once we have real traffic, we'll train the AI-based version."*

That's a mature engineering answer, not a cop-out.

---

## 🔄 Combined Effect of All 3 Layers

Let's trace a full example: User asks "What is your return policy for electronics?"

| Step | What Happens | Token Count |
|---|---|---|
| Original request | System + 10 turns history + 5 RAG chunks + question | 8,200 tokens |
| Layer 1: Cache miss | Question never asked before, continue | — |
| Layer 2: History compress | 8 old turns → 1 summary paragraph | −2,400 tokens |
| Layer 2: RAG rerank | 5 chunks → top 2 chunks | −2,400 tokens |
| Compressed prompt | System + summary + 2 turns + 2 chunks + question | ~3,100 tokens |
| Layer 3: Route | Score = 0.18 → qwen3.5-flash | Using cheapest model |
| **Cost** | 3,100 × $0.10 + 300 × $0.40 / 1M | **$0.00043** |
| **Without TokenTrim** | 8,200 × $0.40 + 300 × $1.20 / 1M | **$0.00364** |
| **Savings** | | **88% cheaper** |

---

## ✅ Key Takeaways

- Layer 3 picks which of the 3 Qwen model tiers to use for each request
- It uses a heuristic scorer based on word count, RAG chunk count, history length, and hard keywords
- The score maps to: < 0.35 → Flash, < 0.70 → Plus, ≥ 0.70 → Max
- The routing decision is always logged with a human-readable reason
- Combined with Layer 2, this achieves ~88% cost reduction in typical workloads

---

➡️ **Next: [08 — The Dashboard](./08_the_dashboard.md)**

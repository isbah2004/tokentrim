# 15. Current Routing Heuristic

## The Scoring Function

The current routing heuristic is implemented in [`score_difficulty()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L33-L46) and produces a score in `[0, 1]`:

```python
def score_difficulty(query: str, rag_chunk_count: int, history_len: int) -> float:
    score = 0.0
    word_count = len(query.split())

    score += min(word_count / 40, 1.0) * 0.4       # longer → harder
    score += min(rag_chunk_count / 5, 1.0) * 0.3   # more context → harder
    score += min(history_len / 10, 1.0) * 0.1      # deeper conversation → harder

    lowered = query.lower()
    if any(sig in lowered for sig in HARD_SIGNALS):
        score += 0.2

    return min(score, 1.0)
```

## Breaking Down the Weights

### Word Count Weight (0.4) — Largest Factor

```
WORD_COUNT_WEIGHT = 0.4
Normalization: word_count / 40
```

| Word Count | Contribution |
|-----------|-------------|
| 5 words   | 0.05 |
| 10 words  | 0.10 |
| 20 words  | 0.20 |
| 40+ words | 0.40 (capped) |

**Rationale**: Longer queries tend to involve more complex requests. A 5-word question ("What time is it?") is almost always simple. A 40-word question with multiple clauses is likely complex.

### RAG Context Weight (0.3) — Second Largest

```
RAG_CONTEXT_WEIGHT = 0.3
Normalization: rag_chunk_count / 5
```

| RAG Chunks | Contribution |
|-----------|-------------|
| 0 chunks  | 0.00 |
| 1 chunk   | 0.06 |
| 3 chunks  | 0.18 |
| 5+ chunks | 0.30 (capped) |

**Rationale**: More retrieved context means the question requires synthesizing more information. Questions that need multiple document chunks are inherently harder than those that need none.

### History Length Weight (0.1) — Smallest Factor

```
HISTORY_LEN_WEIGHT = 0.1
Normalization: history_len / 10
```

| History Turns | Contribution |
|--------------|-------------|
| 0 turns      | 0.00 |
| 3 turns      | 0.03 |
| 5 turns      | 0.05 |
| 10+ turns    | 0.10 (capped) |

**Rationale**: Deeper conversations tend to involve follow-up questions that reference previous context. However, this is the weakest signal because many multi-turn conversations remain simple ("What time is it?" → "And tomorrow?").

### Complexity Keywords (+0.2) — Binary Boost

```python
HARD_SIGNALS = ["compare", "analyze", "why", "explain step by step", "design", "debug"]
```

If any of these appear in the query (case-insensitive), the score gets +0.2.

**Rationale**: These words are strong signals of complex reasoning tasks. "Debug this code" is categorically different from "What color is the sky?"

## How Routing Works

```
Score < 0.35 → qwen3.5-flash  ($0.10 / 1M input)
0.35 ≤ Score < 0.70 → qwen-plus  ($0.40 / 1M input)
Score ≥ 0.70 → qwen3.7-max  ($2.50 / 1M input)
```

## Example Scenarios

### Scenario 1: Simple Question
```
Query: "Hello"
Word count: 1 → (1/40) × 0.4 = 0.01
RAG chunks: 0 → 0.00
History: 0 → 0.00
Keywords: none → 0.00
Score: 0.01 → Flash ✅
```

### Scenario 2: Medium Question
```
Query: "What are the key differences between Python lists and tuples?"
Word count: 10 → (10/40) × 0.4 = 0.10
RAG chunks: 2 → (2/5) × 0.3 = 0.12
History: 3 → (3/10) × 0.1 = 0.03
Keywords: none → 0.00
Score: 0.25 → Flash (borderline)
```

### Scenario 3: Complex Question
```
Query: "Analyze and compare the memory management strategies of Rust and C++, and explain step by step why Rust's borrow checker prevents common bugs"
Word count: 22 → (22/40) × 0.4 = 0.22
RAG chunks: 4 → (4/5) × 0.3 = 0.24
History: 8 → (8/10) × 0.1 = 0.08
Keywords: "analyze", "compare", "explain step by step" → +0.20
Score: 0.74 → Max ✅
```

## What Needs Research

The current heuristic is a reasonable MVP, but the weights and thresholds should be validated against real data. See [Question 16](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/16_determining_routing_values.md) for the proposed benchmarking methodology.

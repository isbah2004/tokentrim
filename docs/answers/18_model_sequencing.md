# 18. Model Sequencing

## The Concept

Model sequencing means establishing a **cost-ordered ladder** of models, from cheapest to most expensive, and always starting at the bottom:

```
Cheapest
   ↓
qwen3.5-flash    ($0.10 / 1M input)
   ↓
qwen-plus        ($0.40 / 1M input)
   ↓
qwen3.7-max      ($2.50 / 1M input)
   ↓
Most expensive
```

## How Sequencing Relates to Routing

**Routing** (current system): A single decision is made upfront. The query is scored, and one model is selected. If Flash is chosen and produces a bad answer, there is no retry.

**Sequencing / Escalation** (v2 upgrade): The system starts with the cheapest model and escalates only when the response quality is insufficient.

```
Query arrives
   ↓
Try Flash first (cheapest)
   ↓
Is the response acceptable?
   ├── YES → Return response (cost: $0.10/1M)
   └── NO
        ↓
   Try Plus (next tier)
        ↓
   Is the response acceptable?
   ├── YES → Return response (cost: $0.40/1M)
   └── NO
        ↓
   Try Max (flagship)
        ↓
   Return response (cost: $2.50/1M)
```

## How to Determine "Acceptable"

The critical question in escalation is: **How does the system know the response is bad without a human reviewing it?**

### Approach 1: Self-Consistency Check
Send the same query twice to the cheap model. If the responses disagree significantly, the model is uncertain → escalate.

### Approach 2: Confidence Scoring
Some models report log-probabilities. Low confidence → escalate.

### Approach 3: Verifier Model
Use a small/cheap model to check the answer:
```
Flash generates answer
   ↓
Flash (as verifier): "Is this answer correct and complete? (yes/no)"
   ↓
If "no" → Escalate to Plus
```

### Approach 4: Heuristic Quality Checks
- Response is too short (< 20 tokens for a complex query)
- Response contains "I don't know" / "I'm not sure"
- Response does not address the query keywords

## Cost Analysis of Escalation

| Scenario | Without Sequencing | With Sequencing |
|----------|-------------------|-----------------|
| Simple query (70% of traffic) | Flash: $0.10/1M | Flash: $0.10/1M (same) |
| Medium query (20% of traffic) | Plus: $0.40/1M | Flash try + Plus: $0.50/1M (slightly more) |
| Hard query (10% of traffic) | Max: $2.50/1M | Flash + Plus + Max: $3.00/1M (slightly more) |

**Wait — isn't escalation more expensive?**

Not necessarily:
- Escalation only happens for queries where the cheap model fails.
- Without sequencing, the router might conservatively send medium queries to Max ($2.50) even though Plus ($0.40) would suffice.
- Sequencing **confirms** that the cheap model fails before spending on the expensive one.

The net effect depends on the router's accuracy. If the router is perfect, sequencing is unnecessary. If the router is imperfect (which heuristic routers always are), sequencing acts as a **safety net** that prevents both under-routing (bad answers) and over-routing (wasted money).

## How This Creates a Cost-Aware Escalation Strategy

The sequence should be automatically established from the pricing table:

```python
# Sort models by input cost (ascending)
model_sequence = sorted(
    config.MODEL_TIERS,
    key=lambda m: m["input"]
)
# Result: [Flash, Plus, Max]
```

This means:
1. Adding a new model (e.g., `qwen-pro` at $1.00/1M) automatically inserts it in the correct position.
2. The system always tries the cheapest option first.
3. Expensive models are only used when cheaper ones have demonstrably failed.

## Implementation for TokenTrim

### Current (MVP): Single-pass routing
```python
decision = pick_model(query, rag_chunks, history)
result = chat_model.generate(decision.model, messages)
```

### Future (v2): Escalation with quality check
```python
for tier in model_sequence:
    result = chat_model.generate(tier.name, messages)
    if quality_check(result, query):
        return result  # good enough at this cost level
# If all fail, return the last (most expensive) result
return result
```

This upgrade path is natural and backward-compatible with the current architecture.

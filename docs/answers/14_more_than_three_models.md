# 14. What If We Have More Than Three Models?

## The Current Design

The system currently hardcodes three model tiers in [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L44-L46):

```python
MODEL_FLASH = "qwen3.5-flash"   # cheap tier
MODEL_PLUS  = "qwen-plus"       # balanced
MODEL_MAX   = "qwen3.7-max"     # flagship
```

And the routing logic in [`pick_model()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L49-L55) uses two thresholds to partition queries into three buckets:

```python
if score < ROUTER_SIMPLE_MAX:     return Flash
if score < ROUTER_MEDIUM_MAX:     return Plus
return Max
```

## The Problem

What if Alibaba releases new models, or we want to support:

```
qwen3.5-flash  →  qwen-plus  →  qwen-pro  →  qwen3.7-max  →  qwen-ultra
```

The current code would need:
- New constants (`MODEL_PRO`, `MODEL_ULTRA`)
- New threshold variables (`ROUTER_HARD_MAX`, `ROUTER_EXPERT_MAX`)
- New `if/elif` branches in `pick_model()`
- Updates to the pricing table

This does not scale.

## The Model-Agnostic Solution

### Define Tiers as a Sorted List

```python
# config.py — model-agnostic design
MODEL_TIERS = [
    {"name": "qwen3.5-flash", "input": 0.10, "output": 0.40, "max_score": 0.35},
    {"name": "qwen-plus",     "input": 0.40, "output": 1.20, "max_score": 0.70},
    {"name": "qwen3.7-max",   "input": 2.50, "output": 7.50, "max_score": 1.00},
]
# Sorted by cost (cheapest first)
```

### Route by Iterating the List

```python
# router.py — model-agnostic routing
def pick_model(query, rag_chunk_count, history_len):
    score = score_difficulty(query, rag_chunk_count, history_len)
    for tier in config.MODEL_TIERS:
        if score < tier["max_score"]:
            return RoutingDecision(model=tier["name"], ...)
    # Fallback to the last (most capable) tier
    return RoutingDecision(model=config.MODEL_TIERS[-1]["name"], ...)
```

### Adding a New Model

To add `qwen-pro` between Plus and Max:

```python
MODEL_TIERS = [
    {"name": "qwen3.5-flash", "input": 0.10, "output": 0.40, "max_score": 0.25},
    {"name": "qwen-plus",     "input": 0.40, "output": 1.20, "max_score": 0.50},
    {"name": "qwen-pro",      "input": 1.00, "output": 3.00, "max_score": 0.75},  # NEW
    {"name": "qwen3.7-max",   "input": 2.50, "output": 7.50, "max_score": 1.00},
]
```

No code changes needed — just configuration.

## Conceptual Tier System

```
Tier 1 → Cheapest / Fastest        (e.g., Flash)
Tier 2 → Low-cost general model    (e.g., Plus)
Tier 3 → More capable model        (e.g., Pro)
Tier 4 → High-capability model     (e.g., Max)
Tier 5 → Flagship model            (e.g., Ultra)
```

The router always selects the **cheapest tier** whose `max_score` is above the query's difficulty score. This ensures:
- Simple queries always go to the cheapest model.
- Only genuinely complex queries reach the expensive models.
- Adding or removing tiers requires zero code changes.

## Should We Implement This Now?

For the hackathon MVP, the current three-tier hardcoded design is **fine**:
- It is simple and easy to explain to judges.
- Three tiers is the current Alibaba lineup.
- The code is clear and testable.

However, the model-agnostic design should be documented as the **v2 upgrade path** because:
- Alibaba will release new models.
- Other providers (if TokenTrim expands) have different tier structures.
- A generic design demonstrates architectural maturity.

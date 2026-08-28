# 17. Model Pricing

## Why Is Model Pricing Important?

Pricing is not just a number on a dashboard — it is a **core input to every decision** TokenTrim makes.

## The Current Pricing Table

From [`config.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/config.py#L48-L54):

```python
# USD per 1,000,000 tokens
PRICING = {
    "qwen3.5-flash": {"input": 0.10, "output": 0.40},
    "qwen-plus":     {"input": 0.40, "output": 1.20},
    "qwen3.7-max":   {"input": 2.50, "output": 7.50},
}
```

| Model | Input Cost (per 1M) | Output Cost (per 1M) | Relative to Flash |
|-------|---------------------|---------------------|--------------------|
| Flash | $0.10 | $0.40 | 1× |
| Plus  | $0.40 | $1.20 | 4× input, 3× output |
| Max   | $2.50 | $7.50 | 25× input, 18.75× output |

## Where Pricing Is Used

### 1. Model Routing (Primary Purpose)

The router's implicit goal is:

> **Select the cheapest model that can handle this query.**

Without pricing, the router cannot determine what "cheapest" means. The 25× cost difference between Flash and Max is the entire economic justification for routing.

### 2. Cost Calculation (Per-Request)

[`estimate_cost()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L58-L61) computes the actual dollar cost of each API call:

```python
def estimate_cost(model, input_tokens, output_tokens):
    price = config.PRICING[model]
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
```

### 3. Naive Baseline (Savings Dashboard)

[`naive_cost()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L64-L78) computes what the request would have cost without TokenTrim — always using the flagship model's pricing:

```python
# "What would this have cost if we did nothing?"
baseline = naive_cost(input_tokens, output_tokens, model=config.MODEL_MAX)
```

### 4. Savings Percentage

```python
savings_pct = (baseline - actual) / baseline * 100
```

Without accurate pricing, this number is meaningless.

### 5. Cost-Aware Escalation (v2)

In the future escalation system, pricing determines whether escalation is worth it:

```
Flash failed → Escalate to Plus?
  Cost increase: 4× → Is the quality improvement worth 4× the cost?
  
Plus also failed → Escalate to Max?
  Cost increase: 6.25× more → Only for genuinely hard problems.
```

## Beyond Routing: Other Purposes of Pricing

| Purpose | How Pricing Helps |
|---------|-------------------|
| **Budget enforcement** | Set a daily/monthly spending limit; routing can refuse to use expensive models when the budget is exhausted |
| **ROI reporting** | Show stakeholders: "TokenTrim saved $X this month" |
| **Alerting** | Detect if a sudden change in query patterns is causing cost spikes |
| **Capacity planning** | Estimate monthly cost from projected query volume |
| **Provider comparison** | If expanding beyond Alibaba, pricing enables cross-provider routing |

## The Key Insight

The router should not just ask:

> "Which model is capable of solving this problem?"

It should ask:

> "What is the **cheapest** model that can solve this problem **reliably**?"

This dual question — **capability + cost** — is the foundation of TokenTrim's value. Without pricing data, the system can only answer the first question, which makes it no different from a basic model selector.

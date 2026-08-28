# 24. Current Model-Routing Techniques in the Industry

## How Modern AI Systems Solve Model Routing

### 1. Rule-Based Routing

**How it works**: Predefined rules map query characteristics to models.

**Examples**:
- **TokenTrim's current approach** — Heuristic scoring based on word count, RAG chunks, history length, and keywords.
- **OpenRouter** — Users can specify model preferences; the platform routes based on model availability and features.

**Pros**: Zero-cost, deterministic, interpretable.
**Cons**: Cannot capture nuanced query complexity; keyword lists are incomplete.

### 2. Classifier-Based Routing

**How it works**: A lightweight ML classifier (logistic regression, small neural net, or fine-tuned small LLM) is trained on labeled (query, best_model) pairs.

**Examples**:
- **Martian's Model Router** — Trains a learned model that predicts which LLM will produce the best response for a given query, considering both quality and cost.
- **Unify AI** — Routes queries across 100+ models using a trained quality predictor that estimates each model's performance on the specific query.
- **RouteLLM** (Anyscale, 2024) — Trains a routing classifier on preference data (e.g., Chatbot Arena) to decide between a strong and weak model.

**Pros**: Learns from real data; generalizes to new query types.
**Cons**: Requires training data and periodic retraining.

### 3. Embedding-Based Routing

**How it works**: Queries are embedded, and the embedding is compared against reference clusters or prototypes for each difficulty level.

**Example**: A system embeds 1,000 labeled queries and trains a k-NN classifier in embedding space. New queries are routed based on which cluster they're nearest to.

**Pros**: Captures semantic similarity; no keyword lists needed.
**Cons**: Requires curated reference sets; embedding quality matters.

### 4. Small-Model-as-Router

**How it works**: A cheap, fast model (like Flash) is used to classify the query before routing.

**Prompt to router model**:
```
Rate the difficulty of this query from 1-5:
"Explain quantum entanglement and its implications for teleportation"
```

**Examples**:
- Several production systems use GPT-3.5-Turbo or Claude Haiku as a router to decide whether a query needs GPT-4 or Claude Opus.
- **Anthropic's routing** reportedly uses a small classifier to allocate between Haiku, Sonnet, and Opus.

**Pros**: Captures nuanced reasoning; the router understands context.
**Cons**: Adds one API call's cost and latency.

### 5. Cascading / Escalation

**How it works**: Start with the cheapest model. If the response is below a quality threshold, escalate.

**Examples**:
- **FrugalGPT** (Stanford, Chen et al., 2023) — Cascades through LLMs in cost order. A learned scoring function decides when to accept the current response or escalate.
- **AutoMix** (CMU, Madaan et al., 2024) — Uses a self-verification mechanism: the small model's response is checked by the same small model; if it fails self-verification, escalate to the larger model.

**Pros**: Guarantees that expensive models are only used when needed.
**Cons**: Adds latency for escalated requests; requires a quality verifier.

### 6. Reinforcement Learning

**How it works**: A routing policy is trained via RL to maximize a reward function that balances response quality and cost.

**Examples**:
- **Hybrid LLM** (Ding et al., 2024) — Uses RL to learn when to use a small vs. large model.

**Pros**: Automatically discovers optimal routing strategies.
**Cons**: Complex to train; reward function design is hard.

### 7. Benchmark-Based Routing

**How it works**: Models are evaluated on standardized benchmarks. Query difficulty is mapped to the benchmark scores to determine which model can handle it.

**Example**: If `qwen3.5-flash` scores 85% on MMLU but only 45% on complex math, queries classified as "math" are routed to Max.

**Pros**: Data-driven; leverages existing evaluation data.
**Cons**: Benchmark performance doesn't always correlate with real-world quality.

### 8. Cost-Aware Routing

**How it works**: The router explicitly optimizes a cost-quality trade-off:

```
minimize: cost(model) + λ × quality_loss(model, query)
```

**Example**: Given a budget of $100/day, the router allocates Max calls to the hardest queries and Flash calls to everything else, staying within budget.

**Pros**: Directly optimizes the business objective.
**Cons**: Requires accurate quality estimates.

## OmniRoute

**OmniRoute** (Meta, 2024) is a research system that combines multiple routing signals:

1. A **complexity classifier** estimates query difficulty.
2. A **model quality predictor** estimates each model's performance on the query.
3. A **cost optimizer** selects the cheapest model whose predicted quality exceeds a threshold.

The key innovation is that it learns routing across a **mixture of models** rather than just deciding between two tiers.

## Summary Table

| Technique | Cost | Latency Added | Accuracy | Used By |
|-----------|------|--------------|----------|---------|
| Rule-based heuristic | Free | None | Low–Medium | TokenTrim (current) |
| Trained classifier | ~Free | ~1ms | Medium–High | Martian, Unify, RouteLLM |
| Embedding clusters | Embedding cost | ~1ms | Medium | Custom implementations |
| Small-model router | 1 cheap API call | ~100ms | High | Anthropic, custom |
| Cascading | 1–N API calls | Variable | Highest | FrugalGPT, AutoMix |
| RL-based | Training cost | ~1ms | High | Research systems |
| Benchmark-based | Free | None | Medium | Unify, custom |
| Cost-aware optimization | Depends | Depends | High | OmniRoute, custom |

## What This Means for TokenTrim

TokenTrim's current rule-based heuristic is the right starting point. The v2 upgrade path should prioritize:

1. **Cascading** (cheapest to add: just retry with a bigger model on failure)
2. **Classifier-based** (train on the benchmark dataset from [Q16](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docs/answers/16_determining_routing_values.md))
3. **Cost-aware optimization** (explicit budget constraints)

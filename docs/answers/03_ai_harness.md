# 3. AI Harness — Model Selection Problem

## The Core Challenge

> **Given a user's problem, how do we decide which AI model to use — and guarantee that the selected model produces accurate, reliable results?**

This is the model-selection problem, and it is the central challenge of any AI harness (also called an AI gateway, model router, or orchestration layer).

## The Problem Flow

```
User's Problem
      ↓
Analyze Difficulty / Requirements
      ↓
Select Appropriate Model
      ↓
Verify Result Accuracy
      ↓
Return Reliable Output
```

## How Modern AI Harnesses Solve This

### 1. Rule-Based Routing (TokenTrim's Current Approach)

This is what TokenTrim implements in [`router.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py):

- A heuristic scoring function (`score_difficulty()`) evaluates query complexity using word count, RAG chunk count, history length, and keyword detection.
- Thresholds map the score to a model tier: Flash (< 0.35), Plus (0.35–0.70), Max (≥ 0.70).

**Pros**: Zero-cost, deterministic, interpretable, no additional API calls.
**Cons**: Cannot capture deep semantic complexity; keyword lists are brittle.

### 2. Classifier-Based Routing

A lightweight classifier (often a fine-tuned small model or even logistic regression) is trained on labeled (query, best_model) pairs to predict which model tier is needed.

**Examples**:
- **Martian** — Uses a learned router that predicts model suitability per query.
- **Unify AI** — Trains routing classifiers on benchmark data across 100+ models.

**Pros**: Learns from real data; captures patterns beyond keywords.
**Cons**: Requires labeled training data; adds inference latency.

### 3. Embedding-Based Routing

The query is embedded and compared against clusters of queries previously associated with each model tier.

**Pros**: Captures semantic similarity; can adapt as new query types emerge.
**Cons**: Requires a curated embedding space and cluster maintenance.

### 4. Cascading / Escalation

Start with the cheapest model. If the response quality is below a threshold (measured by confidence, self-consistency, or a verifier), escalate to the next tier.

**Examples**:
- **FrugalGPT** (Stanford, 2023) — Cascades through models in cost order, stopping when quality is sufficient.
- **AutoMix** (CMU, 2024) — Uses a small verifier to decide when to escalate.

**Pros**: Guarantees that expensive models are only used when cheap ones fail.
**Cons**: Adds latency for escalated requests; requires a quality verifier.

### 5. Small-Model-as-Router

Use a cheap, fast model (e.g., a Flash-tier model) to classify the query before routing it. The router model's sole job is to output a model-tier recommendation.

**Example**: Anthropic's internal routing reportedly uses a small classifier to decide between Haiku, Sonnet, and Opus.

**Pros**: Captures nuanced reasoning; cheap if the router model is small.
**Cons**: Adds one API call of latency and cost per request.

## What TokenTrim Should Consider

TokenTrim's current rule-based approach is appropriate for the hackathon MVP because it is:
- Free (no additional API calls)
- Deterministic (reproducible in tests and demos)
- Fast (zero-latency routing decision)

The documented v2 upgrade path (noted in [`router.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L8-L9)) is to use a Flash-based classifier once there is real traffic to tune against. This is the right trajectory:

```
MVP: Rule-based heuristic (current)
  ↓
v2: Flash-model classifier (cheap, one extra call)
  ↓
v3: Cascading with quality verification (highest accuracy)
```

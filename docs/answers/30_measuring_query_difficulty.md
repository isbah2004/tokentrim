# 30. Core Research Question — How Do We Measure Query Difficulty?

## The Challenge

The router needs to convert a natural-language query into a **single numeric difficulty score** in `[0, 1]` that determines which model handles it. This is a classification problem disguised as a regression problem.

## The Current Approach

[`score_difficulty()`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py#L33-L46) uses four signals:

```
score = word_count_signal × 0.4
      + rag_context_signal × 0.3
      + history_length_signal × 0.1
      + keyword_boost (+0.2)
```

## All Possible Signals for Query Difficulty

### Surface-Level Signals (Easy to Extract, Low Cost)

| Signal | How to Measure | Rationale |
|--------|---------------|-----------|
| **Query length** (words) | `len(query.split())` | Longer queries tend to be more complex |
| **Number of tokens** | Tokenizer output length | More precise than word count |
| **Sentence count** | Split by `.`, `?`, `!` | Multi-sentence queries are often multi-part |
| **Question type** | Detect "what", "why", "how", "compare" | "Why" and "how" are harder than "what" |
| **Presence of lists** | Detect numbered/bulleted items | Multi-part requests |
| **Code presence** | Detect backticks, keywords like `def`, `function` | Code queries need capable models |
| **Mathematical notation** | Detect `+`, `×`, `∫`, `Σ`, equations | Math reasoning is hard |

### Context Signals (From the Pipeline)

| Signal | How to Measure | Rationale |
|--------|---------------|-----------|
| **RAG context size** | Number of retrieved chunks | More context = more synthesis required |
| **Conversation history length** | Number of prior turns | Deep conversations involve complex state |
| **Number of retrieved documents** | Count from retriever | More sources = harder to synthesize |
| **Total input tokens** | Sum of all prompt components | Proxy for overall complexity |

### Semantic Signals (Require Embedding or Classification)

| Signal | How to Measure | Rationale |
|--------|---------------|-----------|
| **Topic classification** | Classify query into categories (math, code, general, creative) | Some topics are inherently harder |
| **Semantic complexity** | Embedding space distance from "simple" query cluster | Learned notion of complexity |
| **User intent** | Classify as question/instruction/conversation | Instructions are often harder than questions |
| **Required output complexity** | Detect "step by step", "with examples", "detailed" | Explicit complexity requests |

### Historical Signals (Require Logged Data)

| Signal | How to Measure | Rationale |
|--------|---------------|-----------|
| **Previous model performance** | Did Flash fail on similar queries? | Learn from past routing decisions |
| **Estimated token generation** | Historical average output length for similar queries | Longer outputs cost more |
| **Failure rate** | How often Flash/Plus fail on this query type | Adjust routing based on observed quality |

## How the Router Could Combine These Signals

### Approach 1: Weighted Linear Combination (Current)

```
score = Σ (weight_i × signal_i)
```

**Pros**: Simple, interpretable, zero-cost.
**Cons**: Cannot capture non-linear interactions (e.g., "short query + code = hard").

### Approach 2: Decision Tree / Random Forest

```
if has_code AND query_length > 20:
    difficulty = HIGH
elif has_math:
    difficulty = HIGH
elif query_length < 10 AND no_context:
    difficulty = LOW
else:
    difficulty = MEDIUM
```

**Pros**: Captures non-linear interactions; interpretable.
**Cons**: Requires labeled training data.

### Approach 3: Small Model Classifier

```
prompt = f"Rate the difficulty of this query from 0.0 to 1.0:\n{query}"
score = flash_model.generate(prompt)  # costs ~$0.00001
```

**Pros**: Captures deep semantic understanding.
**Cons**: Adds one cheap API call per request; not available offline.

### Approach 4: Embedding-Based Clustering

Pre-compute difficulty clusters from benchmark data:
```
Cluster 1 (centroid) → Easy queries → Flash
Cluster 2 (centroid) → Medium queries → Plus
Cluster 3 (centroid) → Hard queries → Max
```

New queries are classified by nearest-cluster assignment.

**Pros**: Semantic understanding without per-query model calls.
**Cons**: Requires curated clusters and periodic updates.

## Recommended Multi-Stage Approach for TokenTrim

### Stage 1 (Current MVP): Heuristic Scoring

The existing `score_difficulty()` function with four signals. Free, deterministic, testable.

### Stage 2 (Post-Hackathon): Enhanced Heuristics

Add more surface-level signals:
```python
# Detect code
if '```' in query or 'def ' in query or 'function ' in query:
    score += 0.15

# Detect math
if any(c in query for c in ['∫', 'Σ', '²', '³', '√']):
    score += 0.15

# Detect multi-part requests
if query.count('?') > 1 or query.count('\n') > 2:
    score += 0.10
```

### Stage 3 (Production): Learned Classifier

Train a lightweight classifier on labeled (query, best_model) pairs from production logs:

```python
from sklearn.ensemble import RandomForestClassifier

# Features: [word_count, token_count, has_code, has_math, rag_chunks, history_len, ...]
# Labels: [0=Flash, 1=Plus, 2=Max]

clf = RandomForestClassifier()
clf.fit(X_train, y_train)

# At inference:
predicted_tier = clf.predict(extract_features(query))
```

This learns the optimal signal weights from real data instead of hand-tuning them.

## The Key Insight

Query difficulty is **not a single number** — it is a multi-dimensional concept that depends on:
- What the query asks (topic, complexity)
- What context is available (RAG, history)
- What the model needs to do (generate code, reason, summarize)
- What quality threshold is acceptable

The current heuristic collapses all of this into one score using four signals and hand-tuned weights. Each upgrade stage adds more signals and better weight optimization, progressively improving routing accuracy without changing the architecture.

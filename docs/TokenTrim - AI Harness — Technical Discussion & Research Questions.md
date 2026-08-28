# TokenTrim / AI Harness — Technical Discussion & Research Questions

## 1. Context Windows and Tokenization

When the context window grows, how does the tokenization process work?

What actually happens behind the scenes when more and more tokens are added to the context?

What is the complete process involved in handling large context windows?

How do Chinese AI models handle extremely large context windows, and how are they able to provide some of the highest context-window limits in the industry?

---

## 2. Automated Testing and CI/CD

For each unit, we can add a trigger so that we do not have to perform manual testing repeatedly.

Whenever changes are pushed, the complete CI/CD pipeline should automatically run.

The idea is:

**Code Change → Trigger → Tests → Build → CI/CD Pipeline**

Once the tests are written properly, the problem of repeatedly performing manual testing is essentially solved.

> "We write the tests once, and after that, we don't have to manually test the same functionality again and again."

---

# 3. AI Harness

AI Harness is becoming increasingly relevant.

The major problem is:

**How do we decide which model should be selected for which problem?**

The selected model should not only be appropriate for the task but should also produce accurate and reliable results.

The main challenge is therefore:

**Problem → Difficulty/Requirements → Appropriate Model → Accurate Result**

We need to investigate how modern AI harnesses solve this model-selection problem.

---

# 4. Database Design

We need to carefully design the database.

Questions we need to answer:

- What type of database should we use?
- What should the schema look like?
- Which data needs to be stored?
- How should vectors be stored?
- How should cached responses be stored?
- How should metadata be structured?
- How will the database scale?
- What indexing strategy should we use?

The database design should be based on the actual requirements of the system rather than choosing a database first and designing around it.

---

# 5. Git and CI/CD

The workflow should be automated through Git and CI/CD.

For example:

**Developer makes changes → Push to Git → CI/CD trigger → Tests run → Build → Deployment**

Once automated tests are properly implemented, every future change can automatically be validated.

---

# 6. Why Do We Need Offline Mode?

We need to clearly define the purpose of offline mode.

The key question is:

**Why are we going offline?**

What problem does offline mode actually solve?

Possible reasons include:

- Demonstrating the system without an internet connection.
- Preventing API failures from breaking the demo.
- Allowing development and testing without API keys.
- Avoiding dependency on external services.
- Providing a fallback when the database is unavailable.
- Making the system resilient during live presentations.
- Testing the routing, caching, and pipeline logic without spending money on API calls.

We need to clearly justify offline mode as part of the architecture rather than treating it merely as a demo feature.

---

# 7. Live vs. Offline Seamless Fallback

The system is designed so that it can continue operating without internet access, an API key, or an external database.

### Automatic Detection

If the `openai` package and `DASHSCOPE_API_KEY` are available, the system makes a real Qwen AI API call.

If the internet or API keys are unavailable, or if:

`TOKENTRIM_OFFLINE=1`

is enabled, the system automatically switches to offline mock modules and an in-memory store.

### No-Crash Guarantee

Even if the internet or database goes down during a live demonstration, the dashboard should not crash.

Instead, the system should seamlessly fall back to offline mode.

This makes the system more reliable for hackathon demonstrations.

---

# 8. Dashboard Baseline — How Do We Calculate Savings?

The savings displayed on the dashboard must be honest and clearly explainable.

### Naive Baseline

We calculate how much the request would have cost if the complete, uncompressed request had been sent to the most expensive flagship model, such as `qwen3.7-max`.

### Actual Cost vs. Baseline

The system compares the actual cost with the baseline cost.

The dashboard should display:

- Baseline cost
- Actual cost
- Percentage saved
- Exact dollar amount saved

### Cache Hits

When a request is served from cache, the system treats the corresponding flagship-model cost as a saved amount.

We need to make sure this calculation is technically and economically defensible.

---

# 9. Can We Ask Questions That Have Already Been Asked?

An important question is:

**Can the system answer a question that has already been asked before?**

If a user asks the exact same question again, the system should ideally detect the previous request and return the cached answer instead of making another model call.

However, we also need to consider paraphrased questions.

For example:

> "What are your hours?"

and

> "When are you open?"

These questions are semantically similar even though the text is different.

Therefore, exact string matching is not enough.

---

# 10. Testing Requirements

Running:

```bash
python -m unittest discover -s tests -t .
```

should result in:

**53 tests passing, with 3 skipped.**

The tests should prove that:

1. The first request generates a response.
2. The second identical request becomes a free cache hit.
3. Simple queries are routed to the Flash model.
4. Complex queries are escalated to the Max model.
5. The offline pipeline works correctly.
6. Routing decisions are deterministic and testable.

---

# 11. Offline Testing Caveat

The offline `HashingEmbeddingProvider` only understands exact or near-duplicate repeated questions.

For example:

> "What are your hours?"

and:

> "What are your opening hours?"

may not necessarily be recognized as semantically identical by the hashing-based provider.

True semantic matching of paraphrased questions requires a real text-embedding model, such as `text-embedding-v4`.

This is an important distinction because semantic similarity is one of the key capabilities of the live Layer 1 caching system.

---

# 12. Main Problem

TokenTrim is a project designed for the **Bano Qabil × Alibaba Cloud AI Hackathon 2026**.

The primary goal is to reduce AI costs when using Alibaba's Qwen AI models.

In simple terms:

**TokenTrim is a smart middleware layer that sits between the user and the Qwen AI models and intelligently reduces token usage and API costs.**

The system attempts to achieve this through:

- Prompt/context trimming
- RAG optimization
- Semantic caching
- Model routing
- Model escalation
- Cost-aware decisions

---

# 13. Routing Thresholds

We need to determine:

**How should routing thresholds actually be selected?**

For example, we currently have:

- `THRESHOLD_FLASH = 0.35`
- `THRESHOLD_PLUS = 0.70`

But where do these numbers come from?

Why should the thresholds be exactly **0.35 and 0.70**?

They should not simply be arbitrary values.

We need to determine whether they should be based on:

- Benchmark results
- Accuracy
- Latency
- Token usage
- Cost
- Query complexity
- Historical requests
- Human evaluation
- Model quality
- Failure rate
- A combination of these factors

We should establish a measurable methodology for selecting these thresholds.

---

# 14. What If We Have More Than Three Models?

The current design assumes three model tiers:

**Flash → Plus → Max**

But we may eventually have more models.

For example:

**Model A → Model B → Model C → Model D → Model E**

Therefore, we need to determine whether our architecture should be designed specifically around three models or whether it should support an arbitrary number of models.

Ideally, the system should be model-agnostic.

Instead of hardcoding:

```text
Flash
Plus
Max
```

we could conceptually define:

```text
Tier 1 → Cheapest / Fastest
Tier 2 → Low-cost general model
Tier 3 → More capable model
Tier 4 → High-capability model
Tier 5 → Flagship model
```

The routing system would then select the cheapest model capable of satisfying the request.

---

# 15. Current Routing Heuristic

The current proposed configuration is:

### Scoring Weights

```text
WORD_COUNT_WEIGHT = 0.4
RAG_CONTEXT_WEIGHT = 0.3
HISTORY_LEN_WEIGHT = 0.1
```

### Complexity Keywords

```text
["analyze", "explain", "compare", "debug", "design"]
```

Complexity keywords add approximately `+0.2` to the score.

### Current Thresholds

```text
THRESHOLD_FLASH = 0.35
THRESHOLD_PLUS = 0.70
```

The proposed behavior is:

```text
Score < 0.35
→ Qwen Flash

0.35 ≤ Score < 0.70
→ Qwen Plus

Score ≥ 0.70
→ Qwen Max
```

However, we need to research and justify these values.

---

# 16. How Should We Determine the Routing Values?

This is one of the most important research questions.

We should not simply choose:

`0.35` and `0.70`

because they look reasonable.

Instead, we should create a benchmark dataset containing different types of queries.

For example:

- Simple factual questions
- Summarization
- Classification
- Coding
- Debugging
- Mathematical reasoning
- Data analysis
- Architecture design
- Complex reasoning

Then we can test each query against different models.

We can measure:

**Accuracy + Cost + Latency + Token Usage**

From these results, we can determine which model provides an acceptable answer at the lowest cost.

The thresholds can then be derived from the benchmark rather than being arbitrary constants.

---

# 17. Model Pricing

Why is model pricing important?

Is pricing required only for routing, or does it have other purposes?

Pricing is important because the system's primary objective is cost optimization.

The router should not only ask:

> "Which model is capable of solving this problem?"

It should also ask:

> "What is the cheapest model that can solve this problem reliably?"

Therefore, model selection should consider both:

**Capability + Cost**

---

# 18. Model Sequencing

Model sequencing is also important.

The system should ideally automatically establish an order from lower-cost models to higher-cost models.

For example:

```text
Cheapest
   ↓
Flash
   ↓
Plus
   ↓
Pro
   ↓
Max
   ↓
Most expensive
```

The system should attempt the lowest-cost suitable model first.

If that model is not suitable for the task, the request should be escalated to the next appropriate model.

This creates a cost-aware escalation strategy.

---

# 19. Embedding Dimension — Why `EMBED_DIM = 768`?

Alibaba's `text-embedding-v4` supports different embedding dimensions through Matryoshka Representation Learning (MRL).

Possible dimensions include:

```text
2048
1024
768
512
256
```

We need to understand why we selected:

```text
EMBED_DIM = 768
```

### Purpose

Compared with 1024 dimensions, 768 dimensions reduce vector storage requirements by approximately 25%.

For example, with 32-bit floating-point values:

```text
1024 dimensions × 4 bytes ≈ 4096 bytes
768 dimensions × 4 bytes ≈ 3072 bytes
```

This also reduces the amount of data involved in similarity calculations.

### Potential Benefits

- Lower memory usage
- Lower storage requirements
- Smaller indexes
- Potentially faster similarity calculations
- Better scalability

### Drawbacks

Reducing dimensionality can potentially reduce semantic retrieval quality.

A lower-dimensional representation may fail to capture some subtle semantic distinctions.

Therefore, we need to investigate:

**What is the actual retrieval-quality difference between 2048, 1024, 768, 512, and 256 dimensions for our specific use case?**

---

# 20. Memory Footprint and MRL

We also need to research:

**What exactly is Matryoshka Representation Learning (MRL)?**

The main reason for studying MRL is that it is directly related to:

- Hardware requirements
- RAM usage
- Vector storage
- Index size
- Search performance
- Retrieval accuracy
- Scalability

We should determine the optimal embedding dimension based on an actual **accuracy vs. memory vs. latency** trade-off.

---

# 21. IVFFLAT Indexing

We need to ask:

**Why are we using IVFFLAT?**

Is IVFFLAT actually the best indexing method for our problem?

We should compare it with alternatives such as:

- HNSW
- IVFFLAT
- Other ANN indexing approaches

We need to determine which indexing method provides the best balance of:

- Recall
- Query latency
- Index build time
- Memory consumption
- Insert/update performance
- Scalability

---

# 22. IVFFLAT Limitation

A current assumption is:

> IVFFLAT is suitable for the hackathon/MVP stage, particularly for a small-to-medium vector dataset.

However, we need to verify this experimentally rather than simply accepting the assumption.

Potential limitations include:

- Recall can depend heavily on index parameters.
- Frequent inserts/updates may require index maintenance.
- Index configuration affects search quality.
- Performance can change as the dataset grows.

We need to research how industry systems handle these limitations.

---

# 23. Main Techniques We Plan to Use

The current architecture includes three major strategies:

### 1. RAG Chunk Reranking

Retrieve relevant chunks first and then rerank them before sending them to the model.

### 2. History Trimming

Remove unnecessary conversation history while preserving the information required to answer the current question.

### 3. Model Routing

Select the cheapest model that is capable of handling the current request.

We need to determine:

**Which of these techniques provide the largest cost savings?**

And:

**What exact strategy should we use for each one?**

---

# 24. Current Model-Routing Techniques in the Industry

We should research the model-routing techniques currently being used in the industry.

Questions include:

- How do modern AI systems classify query difficulty?
- How do they select models?
- Do they use rules?
- Do they use classifiers?
- Do they use embeddings?
- Do they use a small model as a router?
- Do they use reinforcement learning?
- Do they use benchmark-based routing?
- Do they use cost-aware routing?
- Do they use cascading models?

We should also investigate systems such as **OmniRoute** and determine exactly what routing technique it uses.

---

# 25. Are We Actually Doing Something Unique?

We should investigate whether systems already exist that follow a similar architecture.

Our concept includes:

```text
User
 ↓
Cache / Semantic Matching
 ↓
Context Optimization
 ↓
Difficulty Analysis
 ↓
Model Router
 ↓
Cheapest Suitable Model
 ↓
Escalation if Necessary
 ↓
Response
```

We need to research existing systems that follow a similar workflow.

The purpose is not necessarily to prove that our idea is completely unique.

Instead, we should:

1. Study existing architectures.
2. Understand how they solve the same problem.
3. Identify their limitations.
4. Determine what we can improve.
5. Clearly explain what differentiates TokenTrim.

---

# 26. Semantic Cache Hit Rate

An important question is:

**When we get a cache hit, can we confidently return the cached answer?**

Suppose the user asks:

> "What are your working hours?"

We find a previous semantically similar query:

> "When are you open?"

Should we return the previous answer directly?

We need to establish an appropriate similarity threshold.

For example:

```text
Similarity ≥ X
→ Return cached response

Similarity < X
→ Send request to model
```

But we need to determine what `X` should be.

---

# 27. Should Cached Answers Be Stored in pgvector?

If we store previous questions and their answers in pgvector, we can perform semantic similarity searches.

### Benefits

- Avoid repeated API calls.
- Reduce token usage.
- Reduce API costs.
- Reduce latency.
- Improve scalability.
- Potentially answer repeated or paraphrased questions instantly.

### Risks

However, caching responses also creates risks.

For example:

- The cached answer may become outdated.
- A semantically similar question may actually require a different answer.
- A false-positive cache hit could return an incorrect response.
- Similarity thresholds may be difficult to tune.
- Cache invalidation becomes important.

Therefore, we need a robust cache-validation strategy.

---

# 28. Why Are We Using Lazy OpenAI Calls?

We need to understand why we are using lazy API calls.

The basic idea is that we should avoid making an expensive model call unless it is actually necessary.

Instead:

```text
Check Cache
    ↓
Optimize Context
    ↓
Determine Difficulty
    ↓
Select Model
    ↓
Call Model Only When Necessary
```

This approach reduces unnecessary API calls and therefore reduces cost.

We need to determine whether "lazy model invocation" is the correct architectural term and how similar approaches are used in production AI systems.

---

# 29. Batch Indexing and Corpus Processing

We also need to investigate how industry systems handle large-scale corpus indexing.

Questions include:

- How are large document collections embedded?
- Is embedding performed in batches?
- How are vectors inserted into the database?
- How are indexes built?
- Are indexes rebuilt periodically?
- How are new documents added?
- How are deleted documents handled?
- How is incremental indexing implemented?
- How do production systems avoid rebuilding the entire index every time?

We should research industry-standard techniques for:

**Batch Embedding → Batch Insert → Index Build → Incremental Updates**

---

# 30. Core Research Question — How Do We Measure Query Difficulty?

One of the most important questions for TokenTrim is:

**How do we determine how difficult a user's query is?**

We need to convert a natural-language query into a measurable difficulty score.

Possible signals include:

- Query length
- Number of tokens
- Number of reasoning steps
- Presence of complex instructions
- Programming-related terms
- Mathematical requirements
- RAG context size
- Conversation history length
- Number of retrieved documents
- Required output complexity
- Previous model performance
- Estimated token generation
- User intent
- Semantic complexity

The router could then combine these signals into a score.

---

# 31. Final Routing Strategy

The overall strategy should be:

```text
User Query
     ↓
Query Analysis
     ↓
Cache Check
     ↓
Context / History Optimization
     ↓
Difficulty Estimation
     ↓
Cost + Capability Evaluation
     ↓
Select Cheapest Suitable Model
     ↓
Generate Response
     ↓
Evaluate Result
     ↓
Escalate if Necessary
     ↓
Cache Useful Result
```

The key objective is:

> **Do not automatically use the most powerful model. Use the cheapest model that can reliably solve the problem.**

The research should focus on determining how to make this decision accurately, efficiently, and measurably.
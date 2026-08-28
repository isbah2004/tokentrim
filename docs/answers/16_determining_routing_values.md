# 16. How Should We Determine the Routing Values?

## Why We Cannot Just Pick Numbers

Choosing `0.35` and `0.70` because they "look reasonable" is not sufficient for a system that claims to be cost-optimal. The thresholds determine:

- How much money is saved (higher Flash threshold → more savings, but risk of bad answers)
- How much quality is preserved (lower Flash threshold → better answers, but more expensive)
- How defensible the system is to judges ("Why these numbers?" should have a real answer)

## The Proposed Benchmarking Methodology

### Step 1: Create a Benchmark Dataset

Build a dataset of 100–200 queries spanning different difficulty levels:

| Category | Example Queries | Expected Difficulty |
|----------|----------------|-------------------|
| Simple factual | "What is the capital of France?" | Low |
| Summarization | "Summarize this 3-paragraph article" | Low–Medium |
| Classification | "Is this review positive or negative?" | Low |
| Coding (simple) | "Write a function to reverse a string" | Medium |
| Coding (complex) | "Implement a red-black tree with deletion" | High |
| Debugging | "Find the bug in this code and explain why it fails" | High |
| Mathematical reasoning | "Solve this system of three equations" | High |
| Data analysis | "Analyze this dataset and identify trends" | High |
| Architecture design | "Design a microservices architecture for an e-commerce platform" | High |
| Complex reasoning | "Compare and contrast three ML algorithms with trade-offs" | High |

### Step 2: Test Each Query Against All Three Models

For every query in the dataset:

```
Query → qwen3.5-flash → Response_flash
Query → qwen-plus     → Response_plus
Query → qwen3.7-max   → Response_max
```

### Step 3: Measure Quality

For each response, measure:

| Metric | How to Measure |
|--------|---------------|
| **Accuracy** | Human evaluation: Is the answer correct? (1–5 scale) |
| **Completeness** | Does the answer cover all aspects of the question? |
| **Token usage** | Actual prompt + completion tokens reported by the API |
| **Latency** | Time from request to response |
| **Cost** | Calculated from the pricing table |

### Step 4: Determine Model Sufficiency

For each query, determine the **cheapest model that produces an acceptable answer**:

```
If Flash score ≥ 4/5 → Cheapest = Flash
Elif Plus score ≥ 4/5 → Cheapest = Plus
Else → Cheapest = Max
```

### Step 5: Map Difficulty Scores to Model Assignments

Compute the difficulty score for each query using the current `score_difficulty()` function. Then plot:

```
X-axis: Difficulty score (0 to 1)
Y-axis: Cheapest acceptable model (Flash / Plus / Max)
```

### Step 6: Find Optimal Thresholds

The optimal thresholds are the score values that best separate the three model groups:

```
Threshold_flash = Score below which Flash is almost always sufficient
Threshold_plus  = Score below which Plus is almost always sufficient
```

These can be found by:
- **Grid search**: Try every pair of thresholds in 0.05 increments, measure total cost + error rate.
- **ROC analysis**: Treat each threshold as a binary classifier (needs_plus_or_higher? needs_max?) and find the optimal operating point.

### Step 7: Validate

Run the benchmark again with the new thresholds and verify:
- Cost is lower than the naive baseline.
- Quality does not degrade (no simple question gets a wrong answer because Flash was used).
- The thresholds generalize to queries outside the benchmark set.

## Example Outcome

After benchmarking, you might find:

```
Current thresholds: Flash < 0.35, Plus < 0.70
Optimal thresholds: Flash < 0.42, Plus < 0.68
```

This would mean:
- More queries go to Flash (saving more money).
- Slightly fewer queries go to Plus (the boundary is sharper).
- The thresholds are now **data-driven**, not arbitrary.

## For the Hackathon

Even if you don't have time to run a full benchmark, you can:

1. **Test 20–30 representative queries** against all three models.
2. **Manually judge quality** for each response.
3. **Adjust thresholds** if Flash handles more than expected (raise the threshold) or fails too often (lower it).
4. **Document the process** — Judges value methodology over perfection.

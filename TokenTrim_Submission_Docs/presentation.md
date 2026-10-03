# TokenTrim: AI API Cost & Latency Optimization Gateway
**Presentation Outline & Slide Plan**

---

## 🎯 Section 1: The Problem & Introduction (Slides 1-3)

**Slide 1: Title Slide**
* **Title:** TokenTrim: Intelligent Routing & Context Compression for LLMs
* **Subtitle:** Cutting API costs and optimizing latency without sacrificing answer quality.
* **Visual:** Minimalist graphic of coins/tokens being filtered.

**Slide 2: The Problem with Naive LLM Integrations**
* **Bullet Points:**
  * **Exploding Costs:** Sending full chat history and unfiltered RAG chunks wastes input tokens.
  * **Unpredictable Latency:** Heavy prompts slow down the "Time to First Token" (TTFT).
  * **Model Overkill:** Using flagship models (like Qwen-Max or GPT-4) for simple greetings or easy questions is a massive waste of money.
* **Visual:** A pie chart showing how API costs scale linearly with context size.

**Slide 3: Enter TokenTrim**
* **Concept:** A smart API gateway sitting between the user application and the LLM provider.
* **Core Philosophy:** "Right model, right context, right time."
* **Key Offerings:** Semantic caching, history/RAG compression, and dynamic difficulty routing.

---

## 🏗️ Section 2: The 3-Layer Architecture (Slides 4-6)

**Slide 4: Layer 1 — Semantic Cache**
* **Concept:** Stop paying for questions you've already answered.
* **How it works:** Uses vector embeddings to match incoming queries against a database of past Q&As. 
* **Key Metric:** Uses a precise `0.92` cosine similarity threshold to catch paraphrased questions (e.g., "What are your hours?" vs "When do you open?").
* **Visual:** Simple matching diagram (Query -> Embedder -> Vector DB -> Hit/Miss).

**Slide 5: Layer 2 — Context Compressor**
* **Concept:** Send only what the model *actually* needs to know.
* **How it works:**
  * **History Trimming:** Discards old, irrelevant chat turns; compresses verbose system messages.
  * **RAG Pruning:** (Planned) Reranks retrieved document chunks and drops the ones with low relevance scores.
* **Visual:** A funnel showing large text blocks entering and only essential sentences exiting.

**Slide 6: Layer 3 — Dynamic Model Router**
* **Concept:** Stop using a sledgehammer to crack a nut.
* **How it works:** Heuristic scoring (0.0 to 1.0) based on query length, RAG density, history depth, and "hard" keywords (e.g., "debug", "analyze").
* **Routing Logic:**
  * `< 0.35`: **Qwen3.5-Flash** (Simple chat, trivial queries)
  * `0.35 - 0.70`: **Qwen-Plus** (Nuanced questions, light coding)
  * `> 0.70`: **Qwen3.7-Max** (Deep reasoning, complex debugging)
* **Visual:** The Mermaid flowchart mapping scores to model tiers.

---

## 🧪 Section 3: Live Independent Evaluation (Slides 7-10)

**Slide 7: Evaluation Methodology**
* **Approach:** We didn't just use pre-canned datasets. We ran a **live, independent evaluation** hitting real Qwen API endpoints.
* **Techniques:**
  * Controlled constrained outputs to isolate input latency.
  * Deep sweeps (2 to 18 chat turns) to test compression scaling.
  * Adversarial cache probing.
* **Visual:** Icon of a scientist/microscope to emphasize rigorous, unbiased testing.

**Slide 8: Result 1 — Massive Input Cost Savings**
* **Finding:** At 18 turns of chat history, TokenTrim achieved a **3.93x compression ratio**.
* **Impact:** Reduced input tokens by **72%** (from 704 to 196 tokens).
* **Takeaway:** Huge, verifiable savings on API input costs for long-running sessions.
* **Visual:** Bar chart comparing Input Tokens (Uncompressed vs. Compressed).

**Slide 9: Result 2 — The Latency Reality Check**
* **Finding:** While input tokens were slashed, *overall latency wasn't always faster*.
* **Why?** LLM output generation dominates latency. A denser, compressed prompt sometimes causes the model to generate a *longer* response, masking the input speedup. Network jitter also plays a massive role.
* **Takeaway:** Trimming is primarily a **cost-saving** mechanism, not a magic bullet for latency.
* **Visual:** Line graph showing latency fluctuating regardless of input size, dominated by output length.

**Slide 10: Result 3 — Routing Economics**
* **Finding:** Flash is **~50x cheaper** and **7x faster** than Max.
* **Observation:** The router correctly identified and routed 100% of our trivial queries to Flash.
* **Observation:** Our custom heuristic overhead was effectively zero (0.02ms).
* **Visual:** Comparison table of Model Cost vs. Latency.

---

## 🐛 Section 4: Discoveries & Fixes (Slides 11-12)

**Slide 11: Uncovering Hidden Bugs**
*Our rigorous evaluation uncovered structural flaws in the current codebase:*
* **Bug 1: The Dormant RAG Path:** The `rerank_chunks` function requires embeddings, but the pipeline passes raw strings. RAG pruning is silently bypassed!
* **Bug 2: The Cache Seeding Trap:** `skip_cache=True` completely bypasses the write mechanism (`store_answer`), meaning there is no way to pre-warm the cache with FAQs without making real, expensive API calls.

**Slide 12: The "15-Word Rule" Routing Flaw**
* **Discovery:** The router relies heavily on query word count. 
* **The Flaw:** We proved mathematically that any query under 15 words *always* routes to the cheapest model, even if it contains complex keywords like "analyze" or "debug".
* **Impact:** Short, expert queries get under-routed, resulting in poorer answers or ironically longer generation times from the cheap model trying to compensate.

---

## 🚀 Section 5: The Road Ahead (Slide 13)

**Slide 13: Next Steps & Future Roadmap**
* **Fix the RAG Pipeline:** Wire up embeddings to enable true chunk pruning.
* **Cache Management API:** Build a dedicated `/seed` endpoint for pre-warming FAQs.
* **Revamp the Router:** Increase keyword weight bonuses so short, complex queries correctly upgrade to Qwen-Plus/Max.
* **Implement Output Streaming:** To combat the output generation latency discovered in our eval.

**Slide 14: Q&A / Thank You**
* Link to GitHub Repo.
* Contact Information.

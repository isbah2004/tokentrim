# TokenTrim: AI API Cost & Latency Optimization Gateway
**Presentation Outline & Slide Plan**

---

## 🎯 Section 1: The Problem & Introduction (Slides 1-3)

**Slide 1: Title Slide**
* **Title:** TokenTrim: Intelligent Routing & Context Compression for LLMs
* **Subtitle:** Cutting API costs and optimizing latency without sacrificing answer quality.
* **Visual:** Minimalist graphic of coins/tokens being filtered.
* **Speaker Notes:** "Hello everyone. Today I'm excited to present TokenTrim. As AI integration becomes standard in software, teams are running into two massive walls: skyrocketing API costs and sluggish latency. TokenTrim is our solution—a smart gateway that sits between your app and the LLM, designed to cut costs and optimize speed without losing the quality of the answers."

**Slide 2: The Problem with Naive LLM Integrations**
* **Bullet Points:**
  * **Exploding Costs:** Sending full chat history and unfiltered RAG chunks wastes input tokens.
  * **Unpredictable Latency:** Heavy prompts slow down the "Time to First Token" (TTFT).
  * **Model Overkill:** Using flagship models (like Qwen-Max or GPT-4) for simple greetings or easy questions is a massive waste of money.
* **Visual:** A pie chart showing how API costs scale linearly with context size.
* **Speaker Notes:** "Let's look at how most apps talk to LLMs today. It's naive. If a user says 'hello', the app sends their entire 20-turn chat history, plus 5 chunks of RAG context, to a flagship model. You end up paying for a thousand tokens just to get the model to say 'Hi back'. This explodes costs, it kills latency because the model has to process all that junk, and frankly, using a frontier model for a simple greeting is severe overkill."

**Slide 3: Enter TokenTrim**
* **Concept:** A smart API gateway sitting between the user application and the LLM provider.
* **Core Philosophy:** "Right model, right context, right time."
* **Key Offerings:** Semantic caching, history/RAG compression, and dynamic difficulty routing.
* **Speaker Notes:** "Enter TokenTrim. We built a gateway that intercepts the request before it hits the LLM. Our philosophy is 'Right model, right context, right time.' We do this in three layers: we cache semantically similar queries, we actively compress the chat history and RAG data, and we dynamically route the query to a model whose capability actually matches the difficulty of the question."

---

## 🏗️ Section 2: The 3-Layer Architecture (Slides 4-6)

**Slide 4: Layer 1 — Semantic Cache**
* **Concept:** Stop paying for questions you've already answered.
* **How it works:** Uses vector embeddings to match incoming queries against a database of past Q&As. 
* **Key Metric:** Uses a precise `0.92` cosine similarity threshold to catch paraphrased questions (e.g., "What are your hours?" vs "When do you open?").
* **Visual:** Simple matching diagram (Query -> Embedder -> Vector DB -> Hit/Miss).
* **Speaker Notes:** "Layer 1 is the Semantic Cache. The cheapest API call is the one you don't make. Instead of simple string matching, we embed the user's query and do a vector search against past answers. We found that a cosine similarity threshold of 0.92 is the sweet spot—it perfectly catches paraphrased questions like 'What are your hours?' vs 'When do you open?' while avoiding false positives."

**Slide 5: Layer 2 — Context Compressor**
* **Concept:** Send only what the model *actually* needs to know.
* **How it works:**
  * **History Trimming:** Discards old, irrelevant chat turns; compresses verbose system messages.
  * **RAG Pruning:** (Planned) Reranks retrieved document chunks and drops the ones with low relevance scores.
* **Visual:** A funnel showing large text blocks entering and only essential sentences exiting.
* **Speaker Notes:** "If the cache misses, we move to Layer 2: The Context Compressor. Here, we look at the RAG chunks and the chat history. Why send 10 turns of history if the user changed the topic 2 turns ago? We dynamically trim the context window down to the bare essentials. Think of it as a funnel that distills the prompt before the LLM ever sees it."

**Slide 6: Layer 3 — Dynamic Model Router**
* **Concept:** Stop using a sledgehammer to crack a nut.
* **How it works:** Heuristic scoring (0.0 to 1.0) based on query length, RAG density, history depth, and "hard" keywords (e.g., "debug", "analyze").
* **Routing Logic:**
  * `< 0.35`: **Qwen3.5-Flash** (Simple chat, trivial queries)
  * `0.35 - 0.70`: **Qwen-Plus** (Nuanced questions, light coding)
  * `> 0.70`: **Qwen3.7-Max** (Deep reasoning, complex debugging)
* **Visual:** The Mermaid flowchart mapping scores to model tiers.
* **Speaker Notes:** "Finally, Layer 3 is the Dynamic Router. We score the query's complexity from 0 to 1 based on length, RAG depth, and keywords like 'debug' or 'analyze'. A simple 'hello' scores a 0.05 and gets routed to the blazing fast Qwen-Flash model. A deep coding question scores a 0.8 and gets routed to the flagship Qwen-Max model. This ensures we only pay premium prices for premium questions."

---

## 🧪 Section 3: Live Independent Evaluation (Slides 7-10)

**Slide 7: Evaluation Methodology**
* **Approach:** We didn't just use pre-canned datasets. We ran a **live, independent evaluation** hitting real Qwen API endpoints.
* **Techniques:**
  * Controlled constrained outputs to isolate input latency.
  * Deep sweeps (2 to 18 chat turns) to test compression scaling.
  * Adversarial cache probing.
* **Visual:** Icon of a scientist/microscope to emphasize rigorous, unbiased testing.
* **Speaker Notes:** "To prove this works, we didn't just trust unit tests. We built an independent evaluation harness and ran live tests against the actual Qwen API. We constrained outputs to isolate input processing time, we swept history depths from 2 to 18 turns to watch the compression curve, and we threw adversarial questions at the cache to see if it would break."

**Slide 8: Result 1 — Massive Input Cost Savings**
* **Finding:** At 18 turns of chat history, TokenTrim achieved a **3.93x compression ratio**.
* **Impact:** Reduced input tokens by **72%** (from 704 to 196 tokens).
* **Takeaway:** Huge, verifiable savings on API input costs for long-running sessions.
* **Visual:** Bar chart comparing Input Tokens (Uncompressed vs. Compressed).
* **Speaker Notes:** "The results on cost were phenomenal. Look at Slide 8. When a user reached an 18-turn conversation, our compressor achieved a 3.93x compression ratio. We slashed the input tokens being sent to the LLM by 72%—from over 700 tokens down to under 200. Over millions of API calls, that is a massive reduction in your cloud bill."

**Slide 9: Result 2 — The Latency Reality Check**
* **Finding:** While input tokens were slashed, *overall latency wasn't always faster*.
* **Why?** LLM output generation dominates latency. A denser, compressed prompt sometimes causes the model to generate a *longer* response, masking the input speedup. Network jitter also plays a massive role.
* **Takeaway:** Trimming is primarily a **cost-saving** mechanism, not a magic bullet for latency.
* **Visual:** Line graph showing latency fluctuating regardless of input size, dominated by output length.
* **Speaker Notes:** "But we also want to be fully transparent about latency. While we successfully cut the prompt size, the wall-clock latency wasn't always faster. Why? Because output token generation is by far the slowest part of an LLM call. Sometimes, giving the model a denser, compressed prompt actually caused it to write a longer answer, which completely masked the time we saved on the input side. So, trimming is definitively a cost-saver, but it's not a magic latency bullet."

**Slide 10: Result 3 — Routing Economics**
* **Finding:** Flash is **~50x cheaper** and **7x faster** than Max.
* **Observation:** The router correctly identified and routed 100% of our trivial queries to Flash.
* **Observation:** Our custom heuristic overhead was effectively zero (0.02ms).
* **Visual:** Comparison table of Model Cost vs. Latency.
* **Speaker Notes:** "Where we did see massive latency and cost wins was in the Routing layer. In our tests, Qwen-Flash was 50 times cheaper and 7 times faster than Qwen-Max. Our router successfully identified trivial queries and kept them on Flash. The best part? Running our routing heuristic locally only adds 0.02 milliseconds of overhead. It's essentially free to run."

---

## 🐛 Section 4: Discoveries & Fixes (Slides 11-12)

**Slide 11: Uncovering Hidden Bugs**
*Our rigorous evaluation uncovered structural flaws in the current codebase:*
* **Bug 1: The Dormant RAG Path:** The `rerank_chunks` function requires embeddings, but the pipeline passes raw strings. RAG pruning is silently bypassed!
* **Bug 2: The Cache Seeding Trap:** `skip_cache=True` completely bypasses the write mechanism (`store_answer`), meaning there is no way to pre-warm the cache with FAQs without making real, expensive API calls.
* **Speaker Notes:** "Because we built an independent eval, we actually uncovered two silent bugs in the system. First, the RAG pruner is currently dormant—it requires embeddings to work, but the pipeline is only passing raw strings. Second, the cache seeding logic is broken. If you try to pre-warm the cache with an FAQ, the system bypasses the write operation entirely. Both are easy fixes, but critical finds."

**Slide 12: The "15-Word Rule" Routing Flaw**
* **Discovery:** The router relies heavily on query word count. 
* **The Flaw:** We proved mathematically that any query under 15 words *always* routes to the cheapest model, even if it contains complex keywords like "analyze" or "debug".
* **Impact:** Short, expert queries get under-routed, resulting in poorer answers or ironically longer generation times from the cheap model trying to compensate.
* **Speaker Notes:** "We also discovered a structural flaw in the router math, which we're calling the '15-Word Rule'. Because the router relies heavily on word count, we proved that any query under 15 words will always be routed to the cheapest model, even if it contains expert keywords like 'debug' or 'analyze'. This means a 13-word expert question gets sent to the basic model, which might struggle or write a rambling answer trying to figure it out."

---

## 🚀 Section 5: The Road Ahead (Slide 13)

**Slide 13: Next Steps & Future Roadmap**
* **Fix the RAG Pipeline:** Wire up embeddings to enable true chunk pruning.
* **Cache Management API:** Build a dedicated `/seed` endpoint for pre-warming FAQs.
* **Revamp the Router:** Increase keyword weight bonuses so short, complex queries correctly upgrade to Qwen-Plus/Max.
* **Implement Output Streaming:** To combat the output generation latency discovered in our eval.
* **Speaker Notes:** "So where do we go from here? Our immediate roadmap is to fix these discoveries. We'll wire up the embeddings for the RAG pipeline, build a dedicated API to seed the cache with FAQs, and tweak the router math to give more weight to expert keywords so short queries get routed correctly. Finally, we want to implement output streaming to hide that output generation latency from the user."

**Slide 14: Q&A / Thank You**
* Link to GitHub Repo.
* Contact Information.
* **Speaker Notes:** "That's TokenTrim. We're excited about the cost savings we've already proven, and we're ready to tackle the remaining roadmap. Thank you for your time, and I'll open it up to any questions."

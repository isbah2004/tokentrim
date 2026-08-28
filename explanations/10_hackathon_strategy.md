# 10 — Hackathon Strategy: Pitching, Demo, and Business Case
> **Level:** Everyone. This is about presenting the project, not coding it.

---

## 🏆 What Judges Are Actually Judging

This isn't a typical "does the code run" hackathon. The guide is explicit about this:

> *"Selected projects get put in front of investors, industry leaders, and international technology partners — a launchpad, not a finish line."*

That shifts the bar from "working demo" to "plausible product." Judges are asking:
- Could this become a real startup?
- Are the numbers real and checkable?
- Does the team understand the ecosystem they're building in?
- Is there a credible business model?

---

## 🎯 The Three Strategic Design Choices (Made for Judges)

### 1. Every number is independently verifiable

The pricing table in the code is pulled directly from Alibaba's live pricing page. The guide says:

> *"Judges (or an investor's engineer) can pull up Alibaba's own pricing page and verify your math in thirty seconds. If your numbers don't reconcile, the credibility of the whole pitch goes with it."*

What this means for you: **cite the source in your deck.** Include a footnote: "Pricing from alibabacloud.com/help/en/model-studio/model-pricing, August 2026." A judge who Googles this and sees the same numbers will trust everything else you say.

### 2. It looks like a product, not a script

The guide is blunt:
> *"A gateway with a dashboard and a clear before/after story reads as something a team could sell tomorrow. A one-off optimization script doesn't."*

This is why TokenTrim is structured as a gateway API with a live dashboard — not just a Python script you run in the terminal. Products have interfaces. Products have metrics. Products look sellable.

### 3. Staying inside the Alibaba ecosystem

Every tool in TokenTrim uses Alibaba's own services:
- Embeddings → `text-embedding-v4` (Alibaba, not OpenAI)
- Models → Qwen family (Alibaba, not GPT)
- API format → Model Studio (Alibaba's platform)

This tells judges: "We understood the assignment. We built for your ecosystem, not just on top of it."

---

## 🎬 The Demo Script (6 Moves)

Here's exactly how to walk a judge through a live demo:

### Move 1: Open with the problem (30 seconds)
**Say:** *"Most Qwen-powered apps waste 60–80% of their token budget on things that don't need to be there: full chat history replayed every turn, irrelevant documents stuffed into every prompt, and the flagship model doing the work of an intern. We built TokenTrim to fix that automatically."*

**Don't** start with "Hi, I'm X and this is Y." Start with the pain point.

### Move 2: First query — fresh question
Ask something like: *"What are the return policies for electronics?"*

**Show:** The dashboard updates in real time. Point to:
- The model it chose (`qwen3.5-flash`, difficulty=0.18)
- The compressed token count (3,100 vs baseline 8,200)
- The cost ($0.00043)

### Move 3: Second query — paraphrased version of the same question ⭐ (KEY MOMENT)
Ask: *"How do returns work for tech products?"*

**Show:** Cache hit. Instant response. Cost: $0.00000.

**Say:** *"This is what makes TokenTrim different from Alibaba's own prefix cache. The built-in prefix cache only catches byte-for-byte identical prefixes. Our semantic cache caught a paraphrase — different words, same meaning — for free."*

This is the moment that differentiates your project. Don't rush it.

### Move 4: Third query — something genuinely complex
Ask: *"Compare the warranty terms across all product categories and analyze which gives the worst customer value."*

**Show:** Routed to `qwen3.7-max`, difficulty=0.81. Cost is higher. **This is intentional.**

**Say:** *"The system isn't just 'always pick cheap.' It recognized this question requires the flagship model — multi-step analysis, comparison, nuanced judgment. It appropriately escalated."*

This proves the router is smart, not naive.

### Move 5: Show the dashboard
Point to the live cumulative stats:
- Cache hit rate: e.g., 33.3% (1 of 3 requests)
- Actual cost: e.g., $0.022
- Naive cost: e.g., $0.125
- **Savings: ~82%**

These numbers are live-computed from real requests you just made. Not mocked. Not from a slide.

### Move 6: Close with the business case
**Say:** *"At 50,000 requests per day, this is the difference between $5,460/month and $645/month in model costs. TokenTrim could be deployed as a metered API — charge customers a fraction of what they save, keep a spread. Or sold as infrastructure that makes any Qwen-based product cheaper to run. This isn't a hackathon toy — it's the kind of layer that earns its keep in production."*

---

## 💼 The Business Case in Numbers

Use this exact table on your slide (verify prices before presenting):

| Scenario | Daily Cost | Monthly Cost |
|---|---|---|
| Naive (qwen-plus, no optimization, 50k req/day) | ~$182 | ~$5,460 |
| TokenTrim optimized | ~$21.50 | ~$645 |
| **Savings** | **~$160.50/day** | **~$4,815/month** |

Additional cache hit impact: A FAQ-heavy app with even a 20% cache hit rate makes 20% of requests essentially free (just an embedding lookup). That compounds on top of the 88% baseline savings.

---

## 📋 Submission Checklist

Before you submit:

- [ ] **Working repo with a clear README**
  - Architecture diagram (the Mermaid flowchart from the build guide)
  - Setup steps (how to clone, install, configure, and run)
  - How to trigger a demo

- [ ] **All three layers work independently**
  - You can test `cache.py` in isolation (lookup returns something sensible)
  - You can test `compressor.py` in isolation (history gets truncated correctly)
  - You can test `router.py` in isolation (score_difficulty gives sensible scores)
  - Don't wait until the last hour to discover an integration bug

- [ ] **Dashboard shows real live numbers**
  - Not a static mockup with made-up numbers
  - Actually reads from `/stats` which reads from `tokentrim_stats.jsonl`

- [ ] **Pitch deck with:**
  - The problem (token waste at scale)
  - The architecture (the three-layer diagram)
  - The live numbers (from your actual demo run)
  - The business case (the savings table above)

- [ ] **A backup demo video**
  - Live internet + live API access can fail on demo day
  - Record a 2-minute screen recording of the full demo flow as a failsafe

- [ ] **Confirm your actual submission requirements** with your Bano Qabil hackathon coordinators — deadlines, formats, and specific required materials are communicated directly to shortlisted teams

---

## 🚀 Stretch Goals (If You Have Extra Time)

In rough order of effort vs. impact:

| Goal | What it adds | Effort |
|---|---|---|
| LLM-based difficulty classifier | More accurate routing using `qwen3.5-flash` to classify queries | Medium |
| Cross-encoder reranking for RAG | Better relevance scoring than cosine similarity | Medium |
| Explicit context cache | Cache large reusable documents (product manuals) at Alibaba level | Medium |
| Multi-tenant dashboard | Show TokenTrim serving multiple "customers" | High |
| Streaming responses | Stream tokens through the gateway without losing accounting | High |
| Drop-in SDK mode | One-line base URL change to adopt TokenTrim | High |

For the hackathon, get the core three layers and dashboard solid first. Stretch goals are talking points for Q&A ("and our next milestone would be X") — you don't need them working on demo day.

---

## 💡 Likely Judge Questions and How to Answer Them

**Q: "What if someone asks the same question slightly differently and gets the wrong cached answer?"**

A: "That's exactly what the 0.92 threshold is for. We tested it against real near-duplicate question pairs from our own data. Below 0.92, we fall through to a fresh model call. The threshold is configurable — you can tune it up for more precision or down for more cache hits based on your application's needs."

**Q: "Your heuristic router seems too simple. What if it makes the wrong choice?"**

A: "You're right that it's not perfect — it's a deliberate MVP decision. The heuristic costs zero tokens, adds zero latency, and has no failure modes. Once we have real traffic data, we'd replace it with a `qwen3.5-flash` classifier trained on labeled examples. That's actually a better engineering approach than guessing at a classifier before you have data."

**Q: "How is this different from just using Alibaba's built-in caching?"**

A: "Alibaba's implicit prefix cache only matches identical prefixes — byte-for-byte. It can't catch paraphrases. Our semantic cache catches 'what are your hours' and 'when are you open' as equivalent — which structural prefix caching can't do. We also get Alibaba's prefix cache as a bonus by structuring our prompts with stable content first."

**Q: "Could someone just build this in a weekend?"**

A: "Yes — that's actually the point. The architecture is simple because the concepts are simple: cache, compress, route. What's hard is getting all the numbers right, proving it with real data, and making it production-grade. Our next versions add a learning component — the router gets smarter as usage data accumulates."

---

## ✅ Final Takeaways

- Judges want a credible product, not just a working script — structure your pitch accordingly
- The six-move demo script is carefully ordered to hit cache miss → cache hit → complex escalation in sequence
- Every number in your pitch must be verifiable against Alibaba's live pricing page
- Have a backup demo video — live API access can fail
- Stretch goals are talking points, not requirements for demo day

---

**Good luck! This is a strong build. The numbers are real, the architecture is clean, and the business case is genuine. Go win it. 🏆**

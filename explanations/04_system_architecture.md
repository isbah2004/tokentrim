# 04 — System Architecture: How the Three Layers Fit Together
> **Level:** Beginner. Read files 01–03 first.

---

## 🏠 The Gateway Concept

Before diving into code, let's get the big picture right.

TokenTrim is a **gateway** — it sits between your app and the AI model. Every single user request flows through TokenTrim first. TokenTrim decides:

1. "Have I answered something like this before?" → Return cached answer (free)
2. "How can I shrink the prompt before sending it?" → Compress it
3. "Which model actually needs to handle this?" → Route to the right tier

```
┌─────────────┐         ┌───────────────────────┐         ┌────────────────┐
│             │         │                       │         │                │
│  Your App   │──────→  │  TokenTrim Gateway    │──────→  │  Qwen Model    │
│             │         │  (the 3 layers)       │         │  (if needed)   │
│             │  ←────  │                       │  ←────  │                │
└─────────────┘         └───────────────────────┘         └────────────────┘
```

---

## 🗺️ The Full Flow, Step by Step

Here is exactly what happens when a user sends a message:

```
User sends: "What are your business hours?"
                        │
                        ▼
        ┌───────────────────────────┐
        │   TokenTrim Gateway       │
        │   (FastAPI /chat endpoint)│
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │  LAYER 1: Semantic Cache  │
        │                           │
        │  1. Embed the query       │
        │     (convert to numbers)  │
        │  2. Search the database   │
        │     for similar questions │
        │  3. Similar enough (≥92%)?│
        └───────┬───────────┬───────┘
                │           │
           YES  │           │  NO
                ▼           ▼
        ┌──────────┐  ┌───────────────────────────┐
        │ RETURN   │  │  LAYER 2: Compressor       │
        │ CACHED   │  │                            │
        │ ANSWER   │  │  1. Trim chat history      │
        │ (free!)  │  │     Keep last 2 turns      │
        └──────────┘  │     Summarize older turns  │
                      │  2. Rerank RAG chunks      │
                      │     Keep only top 2        │
                      │     most relevant docs     │
                      │  3. Build optimized prompt │
                      └──────────┬────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────────────┐
                      │  LAYER 3: Model Router        │
                      │                              │
                      │  Score the question's        │
                      │  difficulty (0.0 → 1.0)      │
                      │                              │
                      │  < 0.35 → qwen3.5-flash      │
                      │  < 0.70 → qwen-plus          │
                      │  ≥ 0.70 → qwen3.7-max        │
                      └──────────┬───────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────────────┐
                      │  Send to selected Qwen model  │
                      │  Get response back            │
                      └──────────┬───────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────────────┐
                      │  Log tokens used + cost       │
                      │  Store answer in cache        │
                      │  Return response to user      │
                      └──────────────────────────────┘
```

---

## 📁 How the Code is Organized

The project is split into clean, focused files:

```
tokentrim/
├── app/
│   ├── main.py          ← The front door. /chat and /stats routes live here.
│   ├── config.py        ← Settings: model names, prices, thresholds
│   ├── cache.py         ← Layer 1: SemanticCache class
│   ├── compressor.py    ← Layer 2: History trimmer + RAG reranker
│   ├── router.py        ← Layer 3: Difficulty scorer + model picker
│   ├── qwen_client.py   ← Wrapper around the Qwen API client
│   └── stats.py         ← Records every request for the dashboard
├── static/
│   └── dashboard.html   ← The live savings dashboard
├── scripts/
│   └── batch_index_corpus.py  ← One-time bulk embedding job
├── requirements.txt     ← Python packages needed
└── .env                 ← Your API key (NEVER commit this to git)
```

Each file has ONE job. This is a clean software design principle: each component can be read, tested, and debugged independently.

---

## 🛠️ The Tech Stack Explained

| Tool | What it Does | Why This One? |
|---|---|---|
| **FastAPI** | Creates the web server and API endpoints | Fast to build, modern, async-friendly |
| **PostgreSQL** | The database that stores everything | Reliable, widely used |
| **pgvector** | A PostgreSQL extension that stores and searches vectors | Needed for the semantic cache similarity search |
| **OpenAI Python SDK** | The library that talks to Alibaba's API | Alibaba's API is compatible with OpenAI's format |
| **Chart.js** | JavaScript library for the dashboard charts | Simple, no framework needed |
| **NumPy** | Math library used for similarity calculations | Fast vector math |

---

## 🔄 Two Important Caches (Not the Same Thing!)

The guide mentions two types of caching, and they're very different:

### TokenTrim's Semantic Cache (what you build)
- Stores question → answer pairs in your PostgreSQL database
- Matches based on **meaning** (using embeddings)
- Catches paraphrases: "what are your hours" = "when are you open"
- You control it, you built it

### Alibaba's Implicit Prefix Cache (automatic, free bonus)
- Built into Model Studio automatically
- Only matches **identical text prefixes** (the beginning of your prompt must be byte-for-byte the same)
- If two requests start with the exact same system prompt + documents, Alibaba charges less for the prefix
- You get this for free by structuring your prompts smartly (stable content first)

TokenTrim gets **both** — the semantic cache for paraphrase matching, AND the implicit prefix cache discount for identical prefixes.

---

## 📊 Two API Endpoints

When TokenTrim is running, it exposes two URLs:

| Endpoint | What it does |
|---|---|
| `POST /chat` | Your app sends a message here. TokenTrim optimizes and returns the AI's answer. |
| `GET /stats` | Returns a JSON summary of all requests, costs, savings. The dashboard reads from this. |

---

## ✅ Key Takeaways

- TokenTrim is a gateway — every request goes through it first
- It processes requests through 3 layers in sequence: Cache → Compress → Route
- If Layer 1 (cache) has an answer, Layers 2 and 3 are completely skipped (zero model cost)
- Each layer is its own Python file with a single clear responsibility
- Two types of caching are at play: your semantic cache AND Alibaba's implicit prefix cache

---

➡️ **Next: [05 — Layer 1: The Semantic Cache](./05_layer1_semantic_cache.md)**

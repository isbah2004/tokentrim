# 06 — Layer 2: The Context Compressor
> **Level:** Beginner–Intermediate. Read files 01–05 first.

---

## 🎯 One-Line Summary

If the semantic cache doesn't have an answer, Layer 2 trims the bloat out of the prompt before it gets sent to the AI. Less tokens = lower cost.

---

## 📋 Two Jobs in One Layer

The context compressor has two separate tasks:
1. **History Compression** — Trim the chat history
2. **RAG Reranking** — Keep only the most relevant documents

These run on every cache miss, before the prompt is sent to any model.

---

## Job 1: History Compression

### The Problem Refresher

Every API call requires you to re-send the entire conversation history. A 20-turn chat means turn 20's request includes all 19 previous turns — most of which are old and probably no longer relevant.

### The Solution: Summarize the Old Stuff

```python
def compress_history(
    history: list[Message],
    keep_verbatim: int = 2,       # keep the last 2 turns exactly as they were
    max_summary_chars: int = 400, # summarize older turns into max 400 characters
) -> list[Message]:
```

Here's the strategy:

```
Before (10 turns of full history):

  Turn 1:  "Hi, what's your name?"     ← 50 tokens
  Turn 2:  "I'm your assistant."        ← 30 tokens
  Turn 3:  "What products do you have?" ← 80 tokens
  Turn 4:  [long product list answer]   ← 200 tokens
  Turn 5:  "Tell me about Product A"    ← 40 tokens
  Turn 6:  [Product A details]          ← 300 tokens
  Turn 7:  "What's the price?"          ← 20 tokens
  Turn 8:  "Product A is $49."          ← 30 tokens
  ─────────────── (keep these 2 verbatim) ──────────────
  Turn 9:  "Can I get a discount?"      ← 30 tokens
  Turn 10: "Sure, use code SAVE10"      ← 40 tokens
  
Total: ~820 tokens just for history

After compression:

  [Summary]: "User asked about product catalog, Product A 
               details and pricing ($49)."               ← ~50 tokens (the compressed summary)
  Turn 9:  "Can I get a discount?"      ← 30 tokens (verbatim)
  Turn 10: "Sure, use code SAVE10"      ← 40 tokens (verbatim)

Total: ~120 tokens for history
```

**Saving: ~700 tokens just from history compression**

### The Code Explained

```python
def compress_history(history, keep_verbatim=2, max_summary_chars=400):
    if len(history) <= keep_verbatim:
        return history  # if history is already short, no compression needed
    
    # Split: older turns go into summary, recent turns stay verbatim
    older, recent = history[:-keep_verbatim], history[-keep_verbatim:]
    
    # Join all older turn texts into one long string
    joined = " ".join(m.content for m in older)
    
    # Truncate to max_summary_chars characters
    summary = joined[:max_summary_chars]
    if len(joined) > max_summary_chars:
        summary += "..."  # show that it was truncated
    
    # Return: one summary system message + the recent verbatim turns
    return [Message(role="system", content=f"Earlier conversation summary: {summary}")] + recent
```

> **Guide Note:** This is a "cheap extractive summary" — it just truncates the old text rather than having an LLM intelligently summarize it. A smarter v2 would use `qwen3.5-flash` to generate a proper summary. For the hackathon MVP, simple truncation is good enough and has zero extra cost.

---

## Job 2: RAG Reranking

### What is RAG? (Quick Refresher)

**RAG = Retrieval-Augmented Generation**

Your app has a knowledge base (product docs, FAQ pages, policies, etc.). When a user asks a question:
1. Search the knowledge base for relevant chunks
2. Include those chunks in the prompt as "context"
3. The AI answers using both its training AND your specific documents

### The Problem

A naive implementation retrieves 5 chunks every time and includes all 5:

```
User: "What is the return policy for electronics?"

Retrieved chunks (all 5 included in the prompt):
  Chunk 1: Return policy for clothing ← irrelevant!
  Chunk 2: Return policy for electronics ← relevant ✓
  Chunk 3: Shipping times ← irrelevant!
  Chunk 4: Warranty for electronics ← somewhat relevant
  Chunk 5: Contact information ← irrelevant!
```

3 out of 5 chunks are wasted tokens. They increase cost and can actually **confuse** the AI with irrelevant information.

### The Solution: Rerank and Keep Top 2

```python
def rerank_chunks(
    query_embedding: list[float],     # the 768-number vector for the user's question
    chunks: list[tuple[str, list[float]]],  # list of (chunk_text, chunk_embedding) pairs
    top_k: int = 2,                   # keep only the 2 most relevant chunks
) -> list[str]:
```

This function:
1. Takes the user's query embedding (already computed for the cache lookup)
2. Compares it against each chunk's embedding using cosine similarity
3. Sorts by similarity score (most relevant first)
4. Returns only the top 2 chunk texts

```python
    import numpy as np
    
    q = np.array(query_embedding)  # query as a numpy array for fast math
    scored = []
    
    for text, emb in chunks:
        e = np.array(emb)
        # Cosine similarity formula:
        # dot product / (length of q × length of e)
        sim = float(np.dot(q, e) / (np.linalg.norm(q) * np.linalg.norm(e)))
        scored.append((sim, text))
    
    scored.sort(key=lambda x: x[0], reverse=True)  # sort highest similarity first
    return [text for _, text in scored[:top_k]]      # return just the top_k texts
```

**Result for our example:**
```
Chunk 2: Return policy for electronics → similarity: 0.91 ✓ (kept)
Chunk 4: Warranty for electronics     → similarity: 0.83 ✓ (kept)
Chunk 5: Contact information          → similarity: 0.61 ✗ (dropped)
Chunk 3: Shipping times               → similarity: 0.55 ✗ (dropped)
Chunk 1: Return policy for clothing   → similarity: 0.52 ✗ (dropped)
```

Only 2 chunks go into the prompt instead of 5. Roughly 60% of RAG tokens eliminated.

---

## Job 3: Building the Final Optimized Prompt

```python
def build_prompt(
    system_prompt: str,
    compressed_history: list[Message],
    rag_chunks: list[str],
    query: str,
) -> list[dict]:
    context_block = "\n\n".join(rag_chunks)  # join the 2 kept chunks
    messages = [
        {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context_block}"}
    ]
    messages += [{"role": m.role, "content": m.content} for m in compressed_history]
    messages.append({"role": "user", "content": query})
    return messages
```

Notice the ordering: **system prompt → RAG context → history → user question**

This ordering is intentional. The guide explains:
> *"Structure matters for Alibaba's implicit prefix cache: put the stable content (system prompt, then RAG context) first and the unique, per-request content (the actual question) last."*

**Why?** If two requests share the same system prompt + the same documents, those identical prefixes qualify for Alibaba's automatic prefix cache discount. By putting the stable stuff first and the unique stuff last, you maximize the chance of prefix overlap across requests.

---

## 📊 Combined Savings From Layer 2

For our example request that had 8,200 input tokens before optimization:

| Source | Before | After |
|---|---|---|
| System prompt | 500 tokens | 500 tokens (unchanged) |
| Chat history | 3,000 tokens | ~400 tokens (compressed) |
| RAG chunks | 4,000 tokens (5 chunks) | ~1,600 tokens (2 chunks) |
| User question | 20 tokens | 20 tokens (unchanged) |
| **Total** | **7,520 tokens** | **~2,520 tokens** |

That's a **67% reduction** in input tokens from compression alone — before the model router even picks a cheaper model.

---

## ✅ Key Takeaways

- Layer 2 has two sub-tasks: compress history + rerank RAG chunks
- History compression keeps the last 2 turns verbatim and truncates older turns into a short summary
- RAG reranking scores each retrieved chunk's relevance to the query and keeps only the top 2
- The prompt is built with stable content (system + docs) first, dynamic content (history + question) last — for prefix cache compatibility
- Combined, Layer 2 can eliminate 60–70% of input tokens

---

➡️ **Next: [07 — Layer 3: The Model Router](./07_layer3_model_router.md)**

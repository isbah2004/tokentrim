# 09 — Every Code File in the Project, Explained
> **Level:** Intermediate. This is a complete map of the codebase.

---

## 📁 Project File Map

```
tokentrim/
├── app/
│   ├── main.py              ← The front door (Section 1 below)
│   ├── config.py            ← Settings (Section 2)
│   ├── cache.py             ← Layer 1 (covered in file 05)
│   ├── compressor.py        ← Layer 2 (covered in file 06)
│   ├── router.py            ← Layer 3 (covered in file 07)
│   ├── qwen_client.py       ← API wrapper (Section 3)
│   └── stats.py             ← Logging (covered in file 08)
├── static/
│   └── dashboard.html       ← Frontend (Section 4)
├── scripts/
│   └── batch_index_corpus.py ← Bulk embedding (Section 5)
├── requirements.txt         ← Dependencies (Section 6)
└── .env                     ← Secrets (Section 7)
```

---

## 1. `app/main.py` — The Front Door

This is the most important file. It wires all the layers together.

### What It Does
- Creates the FastAPI web application
- Defines the `/chat` and `/stats` endpoints
- Orchestrates Layer 1 → Layer 2 → Layer 3 → Response

### The `/chat` Endpoint, Step by Step

```python
@app.post("/chat")
def chat(req: ChatRequest, cache: SemanticCache):
    t0 = time.time()  # start timing (for latency logging)
```

**What `ChatRequest` contains:**
```python
class ChatRequest(BaseModel):
    query: str              # the user's current question
    history: list[dict]    # list of past turns [{"role": "user", "content": "..."}, ...]
    rag_chunks: list[str]  # document chunks retrieved from the knowledge base
```

**Step 1: Check the cache**
```python
hit = cache.lookup(req.query)
if hit:
    log_request(cache_hit=True, model=None, input_tokens=0, ...)
    return {"response": hit.response, "cached": True, "similarity": hit.similarity}
```
If the cache has a match → return immediately. No model call, no cost, no further processing.

**Step 2: Compress the context**
```python
history = [Message(**m) for m in req.history]   # convert dicts to Message objects
compressed_history = compress_history(history)   # trim old turns
messages = build_prompt(                          # build the optimized prompt
    system_prompt="You are a helpful assistant.",
    compressed_history=compressed_history,
    rag_chunks=req.rag_chunks,
    query=req.query,
)
```

**Step 3: Route to the right model**
```python
decision = pick_model(req.query, len(req.rag_chunks), len(req.history))
```

**Step 4: Call the AI model**
```python
completion = client.chat.completions.create(
    model=decision.model,   # e.g., "qwen3.5-flash"
    messages=messages       # the compressed, optimized prompt
)
usage = completion.usage    # contains .prompt_tokens and .completion_tokens
cost = estimate_cost(decision.model, usage.prompt_tokens, usage.completion_tokens)
cached_tokens = getattr(usage, "cached_tokens", 0)  # Alibaba's implicit cache hits
```

**Step 5: Store answer in cache, log, return**
```python
response_text = completion.choices[0].message.content
cache.store(req.query, response_text)   # save for future similar questions

log_request(
    cache_hit=False,
    model=decision.model,
    input_tokens=usage.prompt_tokens,
    output_tokens=usage.completion_tokens,
    cost=cost,
    latency=time.time() - t0,
    routing_reason=decision.reason,
)

return {
    "response": response_text,
    "cached": False,
    "model_used": decision.model,
    "routing_reason": decision.reason,
    "tokens": {"input": usage.prompt_tokens, "output": usage.completion_tokens},
    "cost_usd": round(cost, 6),
}
```

The response tells your app:
- The actual answer
- Whether it was cached
- Which model was used
- Why that model was chosen
- Exact token counts and cost

---

## 2. `app/config.py` — Central Settings

This file would contain constants used across the app:
```python
# Model names (so you only need to update in one place)
FLASH_MODEL = "qwen3.5-flash"
PLUS_MODEL = "qwen-plus"
MAX_MODEL = "qwen3.7-max"

# Cache settings
CACHE_SIMILARITY_THRESHOLD = 0.92
EMBED_DIM = 768

# Compressor settings
HISTORY_KEEP_VERBATIM = 2
HISTORY_SUMMARY_CHARS = 400
RAG_TOP_K = 2

# Router thresholds
ROUTER_FLASH_THRESHOLD = 0.35
ROUTER_MAX_THRESHOLD = 0.70
```

Having a central config file means you can tune all of these numbers in ONE place without hunting through multiple files.

---

## 3. `app/qwen_client.py` — The API Wrapper

This is a thin wrapper around the OpenAI client, pre-configured for Alibaba:

```python
import os
from openai import OpenAI

def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
```

Why have a separate file for this? So every file that needs the client just imports `get_client()` — if you ever need to change the base URL or add retry logic, you only change it here.

---

## 4. `static/dashboard.html` — The Frontend

This is a single HTML file with embedded JavaScript. Key components:

```html
<!-- The three charts -->
<canvas id="tokensChart"></canvas>
<canvas id="costChart"></canvas>
<canvas id="cacheChart"></canvas>

<script>
// Fetch stats every 3 seconds and update charts
setInterval(async () => {
    const stats = await fetch('/stats').then(r => r.json());
    
    // Update the token bar chart
    tokensChart.data.datasets[0].data = [
        stats.avg_input_tokens,                    // actual (optimized)
        stats.avg_input_tokens * 3                 // naive estimate (baseline)
    ];
    tokensChart.update();
    
    // Update cost bars
    costChart.data.datasets[0].data = [
        stats.total_cost_usd,
        stats.estimated_naive_cost_usd
    ];
    costChart.update();
    
    // Update the savings percentage display
    document.getElementById('savings').textContent = 
        stats.estimated_savings_pct + '% saved';
        
}, 3000);  // every 3 seconds
</script>
```

The key design principle: **this is not a React app or a complex framework**. It's a single HTML file that calls `/stats` every 3 seconds and updates Chart.js bar charts. Simple, fast to build, easy to demo.

---

## 5. `scripts/batch_index_corpus.py` — Bulk Embedding

This script is run **once before the hackathon demo**, not during live requests.

**Use case:** You have 500 FAQ documents or knowledge base articles. You need to embed all of them (convert them all to 768-number vectors) and store them in PostgreSQL so the compressor's `rerank_chunks()` can use them.

Doing this one by one would be slow and slightly more expensive. The **Batch API** lets you submit all 500 requests at once and Alibaba processes them asynchronously at **50% discount**.

```python
# Create a JSONL file with all embedding requests
file_object = client.files.create(
    file=Path("corpus_batch.jsonl"),  # file containing all your embedding requests
    purpose="batch"
)
# Then submit the batch job
batch = client.batches.create(
    input_file_id=file_object.id,
    endpoint="/v1/embeddings",
    completion_window="24h"
)
# Later, poll until it's done
result = client.batches.retrieve(batch.id)
if result.status == "completed":
    # download and store results in PostgreSQL
    ...
```

**Important caveat from the guide:** Batch mode cannot be combined with context cache discounts, and it's asynchronous (takes hours). It's ONLY for offline/background jobs, never for live chat.

---

## 6. `requirements.txt` — Dependencies

```
fastapi           # the web framework
uvicorn           # the server that runs FastAPI
openai            # the Alibaba-compatible API client
psycopg2-binary   # PostgreSQL connector for Python
numpy             # math library (for cosine similarity)
python-dotenv     # reads .env files
pydantic          # data validation (used by FastAPI)
```

Install all at once:
```bash
pip install -r requirements.txt
```

---

## 7. `.env` — Secrets File

```
DASHSCOPE_API_KEY="sk-your-actual-key-here"
DATABASE_URL="postgresql://user:password@localhost:5432/tokentrim"
```

**CRITICAL:** This file MUST be in `.gitignore`. Never ever commit it to GitHub. If your API key leaks, someone else can use it and YOU pay the bill.

```
# .gitignore
.env
*.jsonl        # the stats log file (can get large)
__pycache__/
```

---

## 8. How to Run It Locally

```bash
# 1. Clone/set up the project
cd tokentrim

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your actual API key

# 4. Create the PostgreSQL database table
psql -U postgres -d tokentrim -f scripts/setup_db.sql

# 5. (Optional) Index your knowledge base
python scripts/batch_index_corpus.py

# 6. Start the server
uvicorn app.main:app --reload --port 8000

# 7. Open the dashboard
# Navigate to: http://localhost:8000/stats    ← raw JSON
# Navigate to: http://localhost:8000/static/dashboard.html ← visual dashboard
```

---

## ✅ Key Takeaways

- `main.py` is the orchestrator that calls all other modules in sequence
- Each module has a single job: cache, compress, route, log
- The `.env` file holds secrets and must NEVER be committed to git
- The `batch_index_corpus.py` script is a one-time setup tool, not a live request handler
- The dashboard is a simple HTML file that polls `/stats` — no heavy framework needed

---

➡️ **Next: [10 — Hackathon Strategy: Pitching, Demo Script, and Business Case](./10_hackathon_strategy.md)**

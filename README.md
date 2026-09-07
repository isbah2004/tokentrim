# TokenTrim

A drop-in **token-optimization gateway** for LLM-powered applications. It sits between your app and API providers (like Alibaba Cloud's Qwen API) and cuts token spend significantly through three optimization layers, visualizing the savings live via a React dashboard.

1. **Semantic Cache** — Skip generation entirely for repeated or semantically similar queries.
2. **Context Compressor** — Trim chat history and rerank RAG context chunks before sending them to the LLM.
3. **Model Router** — Send each query to the cheapest model tier that can handle its complexity.

---

## Project Layout

```
token_optimizer/
├── app/
│   ├── config.py        # Model IDs, pricing table, routing thresholds
│   ├── cache.py         # SemanticCache + embeddings logic
│   ├── compressor.py    # History + RAG compression algorithms
│   ├── router.py        # Difficulty scoring + model selection (qwen-plus vs qwen3.7-max)
│   ├── pipeline.py      # Orchestrates the gateway (Cache -> Compress -> Route)
│   ├── qwen_client.py   # Live API client wrappers
│   └── main.py          # FastAPI endpoints (/chat and /stats)
├── frontend/            # React + Vite visualizer dashboard
│   ├── src/App.jsx      # Main dashboard UI logic
│   └── package.json     # Node dependencies
├── tests/               # Backend integration and unit test suite
│   ├── eval/            # Offline Evaluation Harness
│   │   ├── evaluate_pipeline.py # Core eval runner
│   │   └── datasets/golden_v1.jsonl # 20 edge-case test dataset
│   └── ...              # Component tests
├── .github/workflows/   # CI/CD and Live Eval automation
└── requirements.txt     # Python backend dependencies
```

---

## Performance Results

TokenTrim's routing and compression logic is actively tested against a rigorous **Offline Evaluation Harness**. Current metrics:

- **Routing Tier Accuracy:** 85.7%
- **Semantic Cache Hit F1:** 100.0%
- **Average Compression Ratio:** 1.24x
- **Average Token Savings:** ~83.6%

---

## Prerequisites

- **Python 3.10+** (Backend & Eval Harness)
- **Node.js 18+** (Frontend React Dashboard)
- *(Live mode only)* an **Alibaba Cloud Model Studio** API key set in the `DASHSCOPE_API_KEY` environment variable.

---

## Quickstart

### 1. Backend API & Evaluation Harness

Install dependencies and run the offline evaluation harness to see the savings logic in action:

```bash
# Setup Python Environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the Offline Evaluation Harness
python -m tests.eval.evaluate_pipeline --dataset tests/eval/datasets/golden_v1.jsonl --output eval-report.json --assert-thresholds

# Run the Backend Unit Tests
python -m unittest discover tests/
```

### 2. Frontend Visualizer Dashboard

Start the React/Vite development server to test the interactive visualizer.

```bash
cd frontend
npm install
npm run dev
```
You can access the UI at `http://localhost:5173`. 

### 3. Run Frontend Tests
```bash
cd frontend
npm run test
```

---

## CI/CD Pipeline

TokenTrim includes automated GitHub Actions workflows:
- **CI Pipeline (`ci.yml`)**: Automatically tests the backend (`unittest`), frontend (`vitest`), and runs the offline evaluation harness on every push and pull request.
- **Live Evaluation (`eval-live.yml`)**: A manually dispatched secure action that evaluates the system against the real live Alibaba Qwen API using GitHub secrets.

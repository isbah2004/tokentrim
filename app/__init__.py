"""TokenTrim — a token-optimization gateway for Qwen-powered apps.

Three layers cut token spend before a request ever reaches a model:
  1. Semantic cache      (app.cache)       — skip generation for repeats/paraphrases
  2. Context compressor  (app.compressor)  — trim history + rerank RAG context
  3. Model router        (app.router)      — send each query to the cheapest capable tier

See docs/ for the per-phase build notes and TokenTrim_Project_Explanation.md
for the conceptual overview.
"""

__version__ = "0.1.0"

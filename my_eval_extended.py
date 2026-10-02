"""
Extended Evaluation — Round 2
==============================
Additional self-designed prompts across all 4 dimensions.
Results will be appended to the live eval report.
"""
import time
import json
from app.cache import SemanticCache, InMemoryVectorStore
from app.embeddings import QwenEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import QwenChatModel
from app import config, router as rt

SEPARATOR = "═" * 72

def make_gateway():
    embedder = QwenEmbeddingProvider()
    chat_model = QwenChatModel()
    store = InMemoryVectorStore()
    cache = SemanticCache(store=store, embedder=embedder)
    return Gateway(cache=cache, chat_model=chat_model)

def section(title):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)

results = {}   # collect everything for the report

# =============================================================================
# EVAL A — EXTENDED: Deeper history (10 turns) to actually show compression win
# =============================================================================
section("EVAL A EXTENDED — Deep History (10 turns) Compression")

DEEP_HISTORY = [
    {"role": "user",      "content": "Can you explain what machine learning is?"},
    {"role": "assistant", "content": "Machine learning is a branch of AI where models learn patterns from data rather than being explicitly programmed. There are three main paradigms: supervised learning (labelled data), unsupervised learning (unlabelled data), and reinforcement learning (reward-based)."},
    {"role": "user",      "content": "What is supervised learning exactly?"},
    {"role": "assistant", "content": "In supervised learning you train a model on input-output pairs. For example, feeding thousands of images labelled 'cat' or 'dog' so the model learns to classify new images. Common algorithms include linear regression, decision trees, support vector machines, and neural networks."},
    {"role": "user",      "content": "How does a neural network work?"},
    {"role": "assistant", "content": "A neural network consists of layers of nodes (neurons). Each node applies a weighted sum of inputs followed by an activation function (like ReLU or sigmoid). Training uses backpropagation to adjust weights via gradient descent, minimising a loss function such as cross-entropy."},
    {"role": "user",      "content": "What is gradient descent?"},
    {"role": "assistant", "content": "Gradient descent is an optimisation algorithm. It computes the gradient of the loss with respect to each weight, then moves the weights in the opposite direction by a step size called the learning rate. Stochastic gradient descent (SGD) processes mini-batches rather than the full dataset, making it faster."},
    {"role": "user",      "content": "What are the main types of neural networks?"},
    {"role": "assistant", "content": "Key architectures: CNNs (convolutional, good for images), RNNs/LSTMs (sequential/time-series), Transformers (attention-based, SOTA for NLP and vision), GANs (generative adversarial, for synthesis), and Autoencoders (for compression and anomaly detection)."},
    {"role": "user",      "content": "Tell me about transformers and attention."},
    {"role": "assistant", "content": "The Transformer (Vaswani et al. 2017) uses multi-head self-attention: each token attends to every other token, computing query-key-value weighted sums. This captures long-range dependencies that RNNs struggled with. Models like BERT, GPT, and T5 all build on this architecture."},
    {"role": "user",      "content": "What is fine-tuning?"},
    {"role": "assistant", "content": "Fine-tuning takes a pre-trained model and continues training it on a smaller, task-specific dataset. Rather than learning from scratch, it adapts the existing weights. Techniques include full fine-tuning, LoRA (low-rank adaptation), and prompt tuning, each offering different trade-offs between cost and performance."},
    {"role": "user",      "content": "What is overfitting?"},
    {"role": "assistant", "content": "Overfitting occurs when a model memorises training data instead of learning general patterns. Signs: low training loss but high validation loss. Mitigations include dropout, L1/L2 regularisation, early stopping, and data augmentation."},
    {"role": "user",      "content": "What evaluation metrics should I use?"},
    {"role": "assistant", "content": "It depends on the task. Classification: accuracy, precision, recall, F1, AUC-ROC. Regression: MSE, RMSE, MAE. NLP: BLEU, ROUGE, perplexity. Object detection: mAP. Always choose metrics that reflect real-world impact, not just model convenience."},
]

QUERY_DEEP = "Give me a three-bullet summary of our entire conversation."

gw_deep = make_gateway()
gw_deep2 = make_gateway()

print(f"\n  History depth : {len(DEEP_HISTORY)} turns")
print(f"  Query         : '{QUERY_DEEP}'")
print()

t0 = time.perf_counter()
r_trim = gw_deep.chat(query=QUERY_DEEP, history=DEEP_HISTORY, skip_cache=True, skip_compression=False)
lat_trim = (time.perf_counter() - t0) * 1000

t0 = time.perf_counter()
r_notrim = gw_deep2.chat(query=QUERY_DEEP, history=DEEP_HISTORY, skip_cache=True, skip_compression=True)
lat_notrim = (time.perf_counter() - t0) * 1000

unc_h = r_trim.tokens['breakdown']['uncompressed']['history']
cmp_h = r_trim.tokens['breakdown']['compressed']['history']
ratio = unc_h / max(cmp_h, 1)

fmt = "  {:<42} {:>14} {:>14}"
print(fmt.format("Metric", "WITH Trim", "WITHOUT Trim"))
print(fmt.format("─"*42, "─"*14, "─"*14))
print(fmt.format("Wall-clock latency (ms)", f"{lat_trim:.0f}", f"{lat_notrim:.0f}"))
print(fmt.format("Input tokens sent", str(r_trim.tokens['input']), str(r_notrim.tokens['input'])))
print(fmt.format("Output tokens", str(r_trim.tokens['output']), str(r_notrim.tokens['output'])))
print(fmt.format("Cost (USD)", f"${r_trim.cost_usd:.6f}", f"${r_notrim.cost_usd:.6f}"))
print(fmt.format("History tokens (uncompressed)", str(unc_h), str(unc_h)))
print(fmt.format("History tokens (compressed)", str(cmp_h), f"{unc_h} (no change)"))
print(f"\n  Compression ratio           : {ratio:.2f}x")
lat_diff = lat_notrim - lat_trim
tok_diff = r_notrim.tokens['input'] - r_trim.tokens['input']
cost_diff = r_notrim.cost_usd - r_trim.cost_usd
print(f"  Input tokens saved          : {tok_diff} tokens")
print(f"  Latency delta               : {lat_diff:+.0f} ms ({'trim faster' if lat_diff>0 else 'trim slower — network jitter'})")
print(f"  Cost delta                  : ${cost_diff:+.6f}")
print(f"\n  Trim response   : {r_trim.response[:160]}")
print(f"  NoTrim response : {r_notrim.response[:160]}")

results['eval_a_ext'] = {
    'history_turns': len(DEEP_HISTORY),
    'trim_lat': lat_trim, 'notrim_lat': lat_notrim,
    'trim_input': r_trim.tokens['input'], 'notrim_input': r_notrim.tokens['input'],
    'trim_cost': r_trim.cost_usd, 'notrim_cost': r_notrim.cost_usd,
    'compression_ratio': ratio, 'hist_unc': unc_h, 'hist_cmp': cmp_h,
    'trim_resp': r_trim.response[:200], 'notrim_resp': r_notrim.response[:200],
}

# =============================================================================
# EVAL A — RAG EXTENDED: Test trim benefit on multi-chunk RAG pruning
# =============================================================================
section("EVAL A RAG EXTENDED — RAG Chunk Pruning (5 chunks, keep top 2)")

RAG_CHUNKS_5 = [
    "Our return policy allows customers to return any product within 30 days of purchase for a full refund. Items must be in original condition with tags attached.",
    "We ship to over 50 countries worldwide. Standard international shipping takes 7-14 business days. Express options are available.",
    "Our loyalty program awards 1 point per dollar spent. Points can be redeemed for discounts at checkout. Platinum members get double points.",
    "Store hours are Monday through Friday 9am to 6pm, Saturday 10am to 4pm, and we are closed on Sundays.",
    "All products carry a 1-year manufacturer warranty. Extended warranties are available at purchase for an additional fee.",
]

RAG_QUERY = "How do I return a product?"

gw_rag = make_gateway()
gw_rag2 = make_gateway()

print(f"\n  RAG chunks     : {len(RAG_CHUNKS_5)} (irrelevant ones should be pruned)")
print(f"  Query          : '{RAG_QUERY}'")
print()

t0 = time.perf_counter()
r_rag_trim = gw_rag.chat(query=RAG_QUERY, rag_chunks=RAG_CHUNKS_5, skip_cache=True, skip_compression=False)
lat_rag_trim = (time.perf_counter() - t0) * 1000

# Without compression: all 5 chunks sent raw
t0 = time.perf_counter()
r_rag_notrim = gw_rag2.chat(query=RAG_QUERY, rag_chunks=RAG_CHUNKS_5, skip_cache=True, skip_compression=True)
lat_rag_notrim = (time.perf_counter() - t0) * 1000

print(fmt.format("Metric", "WITH Trim", "WITHOUT Trim"))
print(fmt.format("─"*42, "─"*14, "─"*14))
print(fmt.format("Wall-clock latency (ms)", f"{lat_rag_trim:.0f}", f"{lat_rag_notrim:.0f}"))
print(fmt.format("Input tokens sent", str(r_rag_trim.tokens['input']), str(r_rag_notrim.tokens['input'])))
print(fmt.format("Cost (USD)", f"${r_rag_trim.cost_usd:.6f}", f"${r_rag_notrim.cost_usd:.6f}"))
print(f"\n  Trim response   : {r_rag_trim.response[:180]}")
print(f"  NoTrim response : {r_rag_notrim.response[:180]}")

results['eval_a_rag'] = {
    'trim_lat': lat_rag_trim, 'notrim_lat': lat_rag_notrim,
    'trim_input': r_rag_trim.tokens['input'], 'notrim_input': r_rag_notrim.tokens['input'],
    'trim_cost': r_rag_trim.cost_usd, 'notrim_cost': r_rag_notrim.cost_usd,
}

# =============================================================================
# EVAL B EXTENDED — Cache: edge cases
# =============================================================================
section("EVAL B EXTENDED — Cache Edge Cases")

SEEDS_B2 = [
    ("How do I reset my password?",   "Go to Settings > Account > Reset Password and follow the email link sent to your registered address."),
    ("What programming language should I learn first?", "Python is recommended for beginners due to its readable syntax and wide ecosystem."),
    ("Explain recursion in one sentence.", "Recursion is when a function calls itself to solve a smaller version of the same problem until a base case is reached."),
]

extended_b_probes = [
    # (seed_index, probe_query, expect_hit, note)
    (0, "How do I reset my password?",                   True,  "exact repeat — must HIT"),
    (0, "My password isn't working, how do I reset it?", True,  "intent paraphrase — should HIT"),
    (0, "How do I change my email address?",             False, "similar domain, different action — MISS"),
    (0, "How do I reset my username?",                   False, "1-word difference, different entity — borderline MISS"),
    (1, "What's the best first programming language?",   True,  "paraphrase — should HIT"),
    (1, "Which coding language is easiest to start with?", True, "heavy paraphrase — should HIT"),
    (1, "What database should I learn first?",           False, "programming→database swap — MISS"),
    (2, "Can you explain recursion briefly?",            True,  "paraphrase — should HIT"),
    (2, "What is a recursive function?",                 True,  "related — borderline HIT"),
    (2, "Explain iteration in one sentence.",            False, "recursion→iteration swap — MISS"),
]

gw_b2 = make_gateway()

# Seed all entries
print("\n  Seeding 3 cache entries...")
seed_resps = []
for seed_q, seed_a, in [(s[0], s[1]) for s in SEEDS_B2]:
    r_seed = gw_b2.chat(query=seed_q, skip_cache=True)
    print(f"  Seeded: '{seed_q[:55]}' → model={r_seed.model_used}")
    seed_resps.append(r_seed)
    time.sleep(0.3)

print()
print(f"  {'Case':<4} {'Query (truncated)':<44} {'Hit?':<6} {'Sim':<8} {'Exp':>6}  {'Note'}")
print(f"  {'─'*4} {'─'*44} {'─'*6} {'─'*8} {'─'*6}  {'─'*38}")

b2_results = []
for seed_idx, probe_q, exp_hit, note in extended_b_probes:
    r = gw_b2.chat(query=probe_q, skip_cache=False)
    sim_str = f"{r.similarity:.4f}" if r.similarity is not None else "none"
    ok = "✅" if r.cached == exp_hit else "❌"
    print(f"  [{seed_idx}]  {probe_q[:42]:<44} {str(r.cached):<6} {sim_str:<8} {'HIT' if exp_hit else 'MISS':>6}  {note}  {ok}")
    b2_results.append({'query': probe_q, 'hit': r.cached, 'sim': r.similarity, 'expected': exp_hit, 'ok': r.cached==exp_hit, 'note': note})
    time.sleep(0.3)

results['eval_b_ext'] = b2_results

# =============================================================================
# EVAL C EXTENDED — Borderline routing: queries that SHOULD cross tiers
# =============================================================================
section("EVAL C EXTENDED — Borderline Routing & Keyword-Length Interaction")

borderline_queries = [
    # (query, rag, hist, note)
    # Short keyword queries — we showed these stay at flash
    ("Why is the sky blue?",                                      0, 0, "short+why → expect flash (score ~0.30)"),
    ("Why does Python use indentation instead of braces?",        0, 0, "longer+why → expect plus if >0.35"),
    ("Compare Python and JavaScript for web development thoroughly", 0, 0, "compare+longer → expect plus"),
    ("Compare Python and JavaScript thoroughly, analyze their ecosystems and explain step by step which one to pick for backend", 0, 0, "multi-keyword, long → expect max"),
    ("Analyze all security vulnerabilities in OAuth2 implementation", 3, 4, "analyze+RAG+history → expect plus/max"),
    ("Debug the following recursive function step by step and explain why it causes a stack overflow: def f(n): return f(n-1)", 2, 3, "debug+explain step by step+code → expect max"),
    ("What is REST?",                                             0, 0, "trivial, no keyword → flash"),
    ("Design a microservices architecture for an e-commerce platform handling 500k daily users", 4, 6, "design+RAG+history → expect max"),
]

print(f"\n  {'Query (truncated)':<56} {'RAG':>4} {'Hist':>5} {'Score':>7} {'Tier':<18}")
print(f"  {'─'*56} {'─'*4} {'─'*5} {'─'*7} {'─'*18}")

border_results = []
for q, rag, hist, note in borderline_queries:
    score = rt.score_difficulty(q, rag, hist)
    decision = rt.pick_model(q, rag, hist)
    lowered = q.lower()
    kw = any(sig in lowered for sig in ["compare","analyze","why","explain step by step","design","debug"])
    kw_str = "🔑" if kw else "  "
    print(f"  {kw_str} {q[:52]:<54} {rag:>4} {hist:>5} {score:>7.2f} {decision.model:<18}  ← {note}")
    border_results.append({'query': q, 'rag': rag, 'hist': hist, 'score': score, 'tier': decision.model, 'kw': kw, 'note': note})

results['eval_c_border'] = border_results

# Now do live calls on 3 selected borderline cases to see actual latency + quality
section("EVAL C EXTENDED — Live Calls: Borderline Tier Impact on Quality")

live_border = [
    ("Why is the sky blue?",     None, "Expected: flash — trivial 'why'"),
    ("Compare Python and JavaScript for web development thoroughly", None, "Expected: flash still (short+compare, score ~0.31)"),
    ("Compare Python and JavaScript thoroughly, analyze their ecosystems and explain step by step which one to pick for backend", None, "Expected: max (multi-keyword, long)"),
]

gw_c3 = make_gateway()
print(f"\n  {'Tier Decided':<18} {'Score':>6} {'In':>5} {'Out':>5} {'Lat ms':>8} {'Cost':>12}  Query")
print(f"  {'─'*18} {'─'*6} {'─'*5} {'─'*5} {'─'*8} {'─'*12}  {'─'*55}")

live_border_results = []
for q, forced, note in live_border:
    score = rt.score_difficulty(q, 0, 0)
    decision = rt.pick_model(q, 0, 0)
    r = gw_c3.chat(query=q, skip_cache=True, forced_tier=forced)
    tier_used = r.model_used or "cache"
    print(f"  {tier_used:<18} {score:>6.2f} {r.tokens['input']:>5} {r.tokens['output']:>5} {r.latency_ms:>8.0f} ${r.cost_usd:>11.6f}  {q[:55]}")
    print(f"    └─ Response: {r.response[:130]}")
    print(f"    └─ {note}")
    print()
    live_border_results.append({'query': q, 'tier': tier_used, 'score': score, 'lat': r.latency_ms, 'cost': r.cost_usd, 'response': r.response[:150], 'note': note})
    time.sleep(0.5)

results['eval_c_live_border'] = live_border_results

# =============================================================================
# EVAL D EXTENDED — Keyword + length combo: when does bonus actually work?
# =============================================================================
section("EVAL D EXTENDED — Keyword × Length Interaction (when does +0.20 cross threshold?)")

HARD_SIGNALS_LIST = ["compare", "analyze", "why", "explain step by step", "design", "debug"]

# Carefully constructed queries at different word counts with same keyword
length_keyword_tests = [
    # (query, keyword, expected_note)
    ("Why?",                                                       "why",     "1 word + keyword → flash"),
    ("Why use Docker?",                                            "why",     "3 words + keyword → flash"),
    ("Why should developers use Docker over VMs?",                 "why",     "7 words + keyword → flash"),
    ("Why should backend developers use Docker containers over traditional virtual machines?", "why", "10 words + keyword → crossing point?"),
    ("Why should backend developers use Docker containers over traditional virtual machines in production deployments?", "why", "13 words + keyword → plus?"),
    ("Why should backend developers consistently prefer Docker containers over traditional VMs in cloud production environments?", "why", "14 words + keyword → plus?"),
    ("Compare PostgreSQL and MySQL",                               "compare", "3 words + compare → flash"),
    ("Compare PostgreSQL and MySQL for high-traffic web apps thoroughly", "compare", "9 words + compare → flash/plus"),
    ("Compare PostgreSQL and MySQL for high-traffic web applications considering performance, scalability, and replication", "compare", "13 words + compare → plus"),
    ("Design a REST API",                                          "design",  "4 words + design → flash"),
    ("Design a REST API for a social media platform",              "design",  "9 words + design → plus?"),
    ("Design a REST API for a social media platform with 1M users, JWT auth, and rate limiting", "design", "16 words + design → max?"),
    # Combo: multiple keywords
    ("Compare and analyze",                                        "multi",   "2 keywords, short → flash"),
    ("Compare and analyze Python vs Rust for systems programming in detail", "multi", "2 keywords, medium → plus"),
    ("Compare and analyze Python vs Rust for systems programming, then design a migration strategy and explain step by step", "multi", "3 keywords, long → max"),
]

print(f"\n  {'Query (truncated)':<56} {'Words':>6} {'KW':>4} {'Score':>7} {'Tier':<18}")
print(f"  {'─'*56} {'─'*6} {'─'*4} {'─'*7} {'─'*18}")

d_ext_results = []
for q, kw_label, note in length_keyword_tests:
    wc = len(q.split())
    score = rt.score_difficulty(q, 0, 0)
    decision = rt.pick_model(q, 0, 0)
    lowered = q.lower()
    kw_fired = any(sig in lowered for sig in HARD_SIGNALS_LIST)
    tier_short = {"qwen3.5-flash": "FLASH", "qwen-plus": "PLUS ⬆", "qwen3.7-max": "MAX ⬆⬆"}[decision.model]
    marker = "←★" if decision.model != "qwen3.5-flash" else ""
    print(f"  {q[:54]:<56} {wc:>6} {kw_label[:4]:>4} {score:>7.2f} {tier_short:<18} {marker}")
    d_ext_results.append({'query': q, 'words': wc, 'kw': kw_label, 'score': score, 'tier': decision.model})

# Find the crossing-point word count for each keyword
print("\n  ── Keyword Crossing Points (word count needed to reach qwen-plus @ score≥0.35) ──")
for kw in ["why", "compare", "analyze", "design", "debug"]:
    for wc in range(1, 60):
        fake_q = " ".join([kw] + ["word"] * (wc - 1))
        s = rt.score_difficulty(fake_q, 0, 0)
        if s >= 0.35:
            print(f"    '{kw}' keyword → needs {wc} words to reach qwen-plus (score={s:.3f})")
            break

results['eval_d_ext'] = d_ext_results

# =============================================================================
# EVAL D LIVE — Compare routing outcome quality: flash vs plus on "compare" query
# =============================================================================
section("EVAL D LIVE — Quality Impact: Flash vs Plus on Same 'Compare' Query")

COMPARE_Q = "Compare PostgreSQL and MySQL for high-traffic web applications considering performance, scalability, and replication"

gw_d = make_gateway()

print(f"\n  Query: '{COMPARE_Q}'")
print(f"  Score: {rt.score_difficulty(COMPARE_Q, 0, 0):.2f} → auto-routes to: {rt.pick_model(COMPARE_Q, 0, 0).model}")
print()

r_flash = gw_d.chat(query=COMPARE_Q, skip_cache=True, forced_tier=config.MODEL_FLASH)
print(f"  FLASH response ({r_flash.latency_ms:.0f}ms, ${r_flash.cost_usd:.6f}, {r_flash.tokens['output']} out-tok):")
print(f"  {r_flash.response[:350]}")
print()
time.sleep(0.5)

r_plus = gw_d.chat(query=COMPARE_Q, skip_cache=True, forced_tier=config.MODEL_PLUS)
print(f"  PLUS response ({r_plus.latency_ms:.0f}ms, ${r_plus.cost_usd:.6f}, {r_plus.tokens['output']} out-tok):")
print(f"  {r_plus.response[:350]}")
print()

print(f"  Latency delta (plus vs flash): +{r_plus.latency_ms - r_flash.latency_ms:.0f}ms")
print(f"  Cost delta    (plus vs flash): +${r_plus.cost_usd - r_flash.cost_usd:.6f}")
print(f"  Output tokens (flash/plus)   : {r_flash.tokens['output']} / {r_plus.tokens['output']}")

results['eval_d_quality'] = {
    'query': COMPARE_Q,
    'flash_lat': r_flash.latency_ms, 'flash_cost': r_flash.cost_usd,
    'flash_out': r_flash.tokens['output'], 'flash_resp': r_flash.response[:350],
    'plus_lat': r_plus.latency_ms, 'plus_cost': r_plus.cost_usd,
    'plus_out': r_plus.tokens['output'], 'plus_resp': r_plus.response[:350],
}

# =============================================================================
# FINAL EXTENDED SUMMARY
# =============================================================================
section("EXTENDED EVALUATION COMPLETE — Results collected")
print(json.dumps({k: (v if not isinstance(v, list) else f"{len(v)} items") for k, v in results.items()}, indent=2))
print()

"""
Eval A — Redo (Controlled & Scientific)
=========================================
Problems with previous run:
  1. Output variance: compressed context → longer model output → masked latency gain
  2. Single-shot: one API call = dominated by network jitter
  3. Only one history depth tested

Fixes:
  1. Constrained output: prompt forces ≤50-word response (eliminates output variance)
  2. Multiple runs: 3 runs per condition, median reported
  3. Depth sweep: 2, 4, 6, 10, 18 turns to show compression curve
  4. RAG controlled: history-only, no RAG (isolate history compression)
"""
import time
import statistics
from app.cache import SemanticCache, InMemoryVectorStore
from app.embeddings import QwenEmbeddingProvider
from app.pipeline import Gateway
from app.qwen_client import QwenChatModel

SEPARATOR = "═" * 72
N_RUNS = 3  # median of 3 to damp jitter

def make_gateway():
    embedder = QwenEmbeddingProvider()
    chat_model = QwenChatModel()
    store = InMemoryVectorStore()
    cache = SemanticCache(store=store, embedder=embedder)
    return Gateway(cache=cache, chat_model=chat_model)

# ─── Full 18-turn ML history ──────────────────────────────────────────────────
FULL_HISTORY = [
    {"role": "user",      "content": "What is machine learning?"},
    {"role": "assistant", "content": "Machine learning is a branch of AI where models learn patterns from data rather than being explicitly programmed. Main paradigms: supervised, unsupervised, and reinforcement learning."},
    {"role": "user",      "content": "What is supervised learning?"},
    {"role": "assistant", "content": "In supervised learning you train a model on labeled input-output pairs — e.g., images labeled cat/dog. Algorithms: linear regression, decision trees, SVMs, neural networks."},
    {"role": "user",      "content": "How does a neural network work?"},
    {"role": "assistant", "content": "A neural network has layers of nodes applying weighted sums + activation functions (ReLU, sigmoid). Training: backpropagation adjusts weights via gradient descent, minimising a loss like cross-entropy."},
    {"role": "user",      "content": "What is gradient descent?"},
    {"role": "assistant", "content": "Gradient descent moves weights in the direction that reduces loss, step size = learning rate. SGD uses mini-batches for speed."},
    {"role": "user",      "content": "What neural network types exist?"},
    {"role": "assistant", "content": "CNNs (images), RNNs/LSTMs (sequences), Transformers (attention, NLP+vision SOTA), GANs (generation), Autoencoders (compression)."},
    {"role": "user",      "content": "Explain transformers and attention."},
    {"role": "assistant", "content": "Transformers use multi-head self-attention: each token attends to all others via query-key-value weighted sums. Captures long-range dependencies. Foundation of BERT, GPT, T5."},
    {"role": "user",      "content": "What is fine-tuning?"},
    {"role": "assistant", "content": "Fine-tuning continues training a pre-trained model on task-specific data. Variants: full fine-tune, LoRA (low-rank adapters), prompt tuning. Trades off cost vs performance."},
    {"role": "user",      "content": "What is overfitting?"},
    {"role": "assistant", "content": "Overfitting: model memorises training data, fails on new data. Fixes: dropout, L1/L2 regularisation, early stopping, data augmentation."},
    {"role": "user",      "content": "What evaluation metrics should I use?"},
    {"role": "assistant", "content": "Classification: accuracy, precision, recall, F1, AUC-ROC. Regression: MSE, RMSE, MAE. NLP: BLEU, ROUGE, perplexity. Detection: mAP. Choose metrics aligned to real-world impact."},
]

# Slice to different depths
DEPTHS = {
    2:  FULL_HISTORY[:2],
    4:  FULL_HISTORY[:4],
    6:  FULL_HISTORY[:6],
    10: FULL_HISTORY[:10],
    18: FULL_HISTORY,
}

# ─── Key: CONSTRAINED query eliminates output variance ────────────────────────
# Previous Eval A used "Give me a three-bullet summary" → variable output length
# This query forces a single short sentence → output tokens will be ~20-30 regardless
CONSTRAINED_QUERY = (
    "Answer in one sentence of at most 15 words: "
    "what was the last topic we discussed?"
)

print(f"\n{SEPARATOR}")
print(f"  EVAL A REDO — Controlled Compression Benchmark")
print(f"{SEPARATOR}")
print(f"\n  Methodology fixes:")
print(f"    ✓ Output constrained to ≤15 words (eliminates output inflation)")
print(f"    ✓ {N_RUNS} runs per condition, median reported (dampen jitter)")
print(f"    ✓ 5 history depths swept: {list(DEPTHS.keys())} turns")
print(f"    ✓ History-only test (no RAG, isolate history compression)")
print(f"\n  Query: \"{CONSTRAINED_QUERY[:70]}\"")

# ─── Sweep ────────────────────────────────────────────────────────────────────
rows = []

print(f"\n  Running sweep... ({len(DEPTHS)} depths × 2 conditions × {N_RUNS} runs = {len(DEPTHS)*2*N_RUNS} calls)")
print()

for depth, history in DEPTHS.items():
    trim_lats   = []
    notrim_lats = []
    trim_in_tok = []
    notrim_in_tok = []
    trim_out_tok = []
    notrim_out_tok = []
    trim_costs  = []
    notrim_costs = []
    hist_unc = hist_cmp = ratio = None

    print(f"  ── Depth {depth:>2} turns ", end="", flush=True)

    for run in range(N_RUNS):
        gw_trim   = make_gateway()
        gw_notrim = make_gateway()

        t0 = time.perf_counter()
        r_trim = gw_trim.chat(
            query=CONSTRAINED_QUERY,
            history=history,
            skip_cache=True,
            skip_compression=False
        )
        trim_lats.append((time.perf_counter() - t0) * 1000)
        time.sleep(0.25)

        t0 = time.perf_counter()
        r_notrim = gw_notrim.chat(
            query=CONSTRAINED_QUERY,
            history=history,
            skip_cache=True,
            skip_compression=True
        )
        notrim_lats.append((time.perf_counter() - t0) * 1000)

        trim_in_tok.append(r_trim.tokens['input'])
        notrim_in_tok.append(r_notrim.tokens['input'])
        trim_out_tok.append(r_trim.tokens['output'])
        notrim_out_tok.append(r_notrim.tokens['output'])
        trim_costs.append(r_trim.cost_usd)
        notrim_costs.append(r_notrim.cost_usd)

        if hist_unc is None:
            hist_unc = r_trim.tokens['breakdown']['uncompressed']['history']
            hist_cmp = r_trim.tokens['breakdown']['compressed']['history']
            ratio = hist_unc / max(hist_cmp, 1)

        print(".", end="", flush=True)
        time.sleep(0.25)

    print(f" done")

    med_trim_lat   = statistics.median(trim_lats)
    med_notrim_lat = statistics.median(notrim_lats)
    med_trim_in    = statistics.median(trim_in_tok)
    med_notrim_in  = statistics.median(notrim_in_tok)
    med_trim_out   = statistics.median(trim_out_tok)
    med_notrim_out = statistics.median(notrim_out_tok)
    med_trim_cost  = statistics.median(trim_costs)
    med_notrim_cost= statistics.median(notrim_costs)

    lat_delta_pct = (med_notrim_lat - med_trim_lat) / med_notrim_lat * 100
    in_saved = med_notrim_in - med_trim_in
    in_saved_pct = in_saved / max(med_notrim_in, 1) * 100

    rows.append({
        'depth': depth,
        'ratio': ratio,
        'hist_unc': hist_unc,
        'hist_cmp': hist_cmp,
        'trim_lat': med_trim_lat,
        'notrim_lat': med_notrim_lat,
        'lat_delta': med_trim_lat - med_notrim_lat,
        'lat_delta_pct': lat_delta_pct,
        'trim_in': med_trim_in,
        'notrim_in': med_notrim_in,
        'in_saved': in_saved,
        'in_saved_pct': in_saved_pct,
        'trim_out': med_trim_out,
        'notrim_out': med_notrim_out,
        'trim_cost': med_trim_cost,
        'notrim_cost': med_notrim_cost,
        'last_trim_resp': r_trim.response[:120],
        'last_notrim_resp': r_notrim.response[:120],
        # raw runs for variance
        'trim_lats': [round(x, 0) for x in trim_lats],
        'notrim_lats': [round(x, 0) for x in notrim_lats],
    })

# ─── Results Table ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print(f"  EVAL A RESULTS — Latency: Trim vs No-Trim (Controlled Output)")
print(SEPARATOR)

hdr = f"  {'Turns':>5} │ {'Ratio':>6} │ {'H-Unc':>6} │ {'H-Cmp':>6} │ {'In-Saved':>9} │ {'T-Lat':>8} │ {'NT-Lat':>8} │ {'Δ Lat':>9} │ {'T-Out':>6} │ {'NT-Out':>6}"
print(hdr)
print("  " + "─"*5 + "┼" + "─"*8 + "┼" + "─"*8 + "┼" + "─"*8 + "┼" + "─"*11 + "┼" + "─"*10 + "┼" + "─"*10 + "┼" + "─"*11 + "┼" + "─"*8 + "┼" + "─"*8)

for r in rows:
    sign = "▼" if r['lat_delta'] > 0 else "▲"  # ▼ = trim was faster
    lat_delta_str = f"{sign}{abs(r['lat_delta']):.0f}ms"
    in_saved_str = f"-{r['in_saved']:.0f} ({r['in_saved_pct']:.0f}%)"
    print(f"  {r['depth']:>5} │ {r['ratio']:>6.2f}× │ {r['hist_unc']:>6} │ {r['hist_cmp']:>6} │ {in_saved_str:>9} │ {r['trim_lat']:>7.0f}ms │ {r['notrim_lat']:>7.0f}ms │ {lat_delta_str:>9} │ {r['trim_out']:>6.0f} │ {r['notrim_out']:>6.0f}")

print()
print("  Legend: T = WITH trim | NT = WITHOUT trim | Δ Lat: ▼ = trim faster, ▲ = trim slower")

# ─── Per-depth run variance ───────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print(f"  EVAL A — Run-by-Run Variance (verify median is stable)")
print(SEPARATOR)
print(f"\n  {'Turns':>5} │ {'Condition':<14} │ {'Run 1':>8} │ {'Run 2':>8} │ {'Run 3':>8} │ {'Median':>8} │ {'StdDev':>8}")
print("  " + "─"*5 + "┼" + "─"*16 + "┼" + "─"*10 + "┼" + "─"*10 + "┼" + "─"*10 + "┼" + "─"*10 + "┼" + "─"*10)
for r in rows:
    tl = r['trim_lats']
    nl = r['notrim_lats']
    print(f"  {r['depth']:>5} │ {'WITH trim':<14} │ {tl[0]:>7.0f}ms │ {tl[1]:>7.0f}ms │ {tl[2]:>7.0f}ms │ {statistics.median(tl):>7.0f}ms │ {statistics.stdev(tl):>7.0f}ms")
    print(f"  {'':>5} │ {'WITHOUT trim':<14} │ {nl[0]:>7.0f}ms │ {nl[1]:>7.0f}ms │ {nl[2]:>7.0f}ms │ {statistics.median(nl):>7.0f}ms │ {statistics.stdev(nl):>7.0f}ms")
    print(f"  {'':>5} │ {'Output tokens':<14} │ trim_out={r['trim_out']:.0f}  │  notrim_out={r['notrim_out']:.0f}  ← variance controlled?")
    print()

# ─── Latency vs Depth chart (ASCII) ──────────────────────────────────────────
print(f"\n{SEPARATOR}")
print(f"  EVAL A — Trim Latency Advantage by History Depth")
print(SEPARATOR)
print()
for r in rows:
    bar_len = int(r['in_saved_pct'] / 2)  # scale: 1% = 0.5 chars
    bar = "█" * bar_len
    faster = r['lat_delta'] > 0
    print(f"  {r['depth']:>2} turns │ compression {r['ratio']:.2f}× │ input -{r['in_saved_pct']:.0f}% {bar}")
    if faster:
        lat_bar = "▼" * max(1, int(abs(r['lat_delta_pct']) / 5))
        print(f"           │ trim FASTER by {abs(r['lat_delta']):.0f}ms ({abs(r['lat_delta_pct']):.1f}%) {lat_bar}")
    else:
        lat_bar = "▲" * max(1, int(abs(r['lat_delta_pct']) / 5))
        print(f"           │ trim SLOWER by {abs(r['lat_delta']):.0f}ms ({abs(r['lat_delta_pct']):.1f}%) {lat_bar} ← jitter still dominates")
    print()

# ─── Compression ratio trend ──────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print(f"  EVAL A — Compression Ratio & Input Token Savings vs History Depth")
print(SEPARATOR)
print()
print(f"  {'Depth':>5} │ {'Ratio':>6} │ {'Raw→Compressed':>20} │ {'Tokens saved':>13} │ {'Cost delta':>12}")
print("  " + "─"*5 + "┼" + "─"*8 + "┼" + "─"*22 + "┼" + "─"*15 + "┼" + "─"*14)
for r in rows:
    cost_delta = r['notrim_cost'] - r['trim_cost']
    cost_str = f"+${cost_delta:.6f}" if cost_delta > 0 else f"-${abs(cost_delta):.6f}"
    direction = "notrim costlier ✅" if cost_delta > 0 else "trim costlier ⚠️"
    print(f"  {r['depth']:>5} │ {r['ratio']:>6.2f}× │ {r['hist_unc']:>6} → {r['hist_cmp']:>6} tokens   │ {r['in_saved']:>6.0f} ({r['in_saved_pct']:.0f}%)   │ {cost_str} ({direction})")

# ─── Responses at max depth ────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print(f"  EVAL A — Quality Check: Last Depth ({rows[-1]['depth']} turns) Responses")
print(SEPARATOR)
last = rows[-1]
print(f"\n  WITH trim response   : {last['last_trim_resp']}")
print(f"  WITHOUT trim response: {last['last_notrim_resp']}")
print()
print(f"  Output tokens (trim / notrim): {last['trim_out']:.0f} / {last['notrim_out']:.0f}")
print(f"  (Good control: difference should be <30 tokens for constrained query)")

print(f"\n{SEPARATOR}")
print(f"  EVAL A REDO COMPLETE")
print(SEPARATOR)

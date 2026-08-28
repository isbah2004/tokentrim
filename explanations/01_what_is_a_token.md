# 01 — What is a Token?
> **Level:** Absolute beginner. No coding knowledge needed.

---

## 🤔 Start With This Analogy

Imagine you hire a human translator. You pay them **per word** they translate. The more words your document has, the more you pay.

AI models work the same way — except instead of **words**, they count **tokens**.

---

## 🔤 So What Exactly is a Token?

A **token** is a small chunk of text. It's not always a full word — it's the smallest unit the AI processes.

Here's a real example. The sentence:

> **"Hello, how are you?"**

...is broken down into roughly **5 tokens** by most AI models:

```
"Hello"  ","  " how"  " are"  " you"  "?"
```

Some rules of thumb:
- **1 token ≈ 4 characters** in English
- **1 token ≈ ¾ of a word**
- Common words like "the", "and" are 1 token each
- Long/rare words might be 2–3 tokens
- In Urdu/Arabic script, one word can be **3–5 tokens** (non-English languages use more)

---

## 💵 Why Does This Matter? (The Billing Part)

Every time your app sends a message to an AI model and gets a response back, the AI company counts the tokens and **charges you**.

There are TWO types of tokens you get billed for:

### 1. Input Tokens (the "prompt")
Everything you SEND to the AI:
- Your system instructions ("You are a helpful assistant...")
- The user's question
- The entire chat history
- Any documents or knowledge you attach

### 2. Output Tokens (the "completion")
Everything the AI SENDS BACK to you:
- The actual response/answer

---

## 📊 A Real Pricing Example

Alibaba Cloud's **Qwen** models (used in this project) have different prices for different model "sizes":

| Model | Input Price | Output Price |
|---|---|---|
| `qwen3.5-flash` (small, fast) | $0.10 per 1 million tokens | $0.40 per 1 million tokens |
| `qwen-plus` (medium, balanced) | $0.40 per 1 million tokens | $1.20 per 1 million tokens |
| `qwen3.7-max` (large, powerful) | $2.50 per 1 million tokens | $7.50 per 1 million tokens |

> **Note:** "Per 1 million tokens" sounds like a lot, but a single chat conversation can easily use 5,000–10,000 tokens. Scale that to 50,000 users per day and it adds up FAST.

---

## 🧮 A Concrete Cost Calculation

Let's say a user asks: *"What are the return policies?"*

Your app sends this to the AI:
```
[System Prompt - 500 tokens]
[Chat History (last 10 turns) - 3,000 tokens]
[Knowledge base docs - 2,000 tokens]
[User's question - 20 tokens]
----------------------------------
Total Input: 5,520 tokens

[AI's answer - 200 tokens]
Total Output: 200 tokens
```

**Cost if using `qwen-plus`:**
```
Input:  5,520 × $0.40 / 1,000,000  = $0.0022
Output:   200 × $1.20 / 1,000,000  = $0.00024
Total per request: ~$0.0024
```

That seems tiny. But if you have **10,000 requests/day**:
```
$0.0024 × 10,000 = $24/day = ~$720/month
```

And this is a **conservative** example. Many real apps send 8,000–10,000 input tokens per request.

---

## 🗑️ Where Tokens Get Wasted (Sneak Preview)

Most apps blindly send:
1. **The entire chat history** — even turns from 2 hours ago that are no longer relevant
2. **All retrieved documents** — even ones that don't actually help answer the question
3. **Every question to the most expensive model** — even when the question is simple ("what's your name?")

**TokenTrim's entire job is to fix these three problems.**

---

## ✅ Key Takeaways

- A token is a small chunk of text (~4 characters or ¾ of a word)
- AI companies charge you per token (both what you send AND what you receive)
- More tokens = more cost
- At scale, wasted tokens = wasted thousands of dollars per month
- **Next up:** What IS the AI model you're sending these tokens to?

---

➡️ **Next: [02 — What is an LLM and an API?](./02_what_is_an_llm_and_api.md)**

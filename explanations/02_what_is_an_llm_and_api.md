# 02 — What is an LLM, an API, and Model Studio?
> **Level:** Absolute beginner.

---

## 🤖 What is an LLM?

**LLM** stands for **Large Language Model**. It's the technology behind AI chatbots like ChatGPT, Gemini, and in this project — **Qwen**.

Think of an LLM like an incredibly well-read person who:
- Has read billions of documents, articles, code files, and books
- Can have a conversation with you about anything
- Can write, summarize, explain, translate, debug code, and more
- But needs you to **describe the conversation from scratch every single time** — it has no persistent memory between sessions (unless you manually send the history)

---

## 🏗️ The Sizes of LLMs (Why There Are Different Tiers)

LLMs come in different sizes. Bigger = smarter but more expensive and slower. Smaller = faster and cheaper but less capable.

The Qwen family used in TokenTrim:

| Model | Size | Best For |
|---|---|---|
| `qwen3.5-flash` | Small & fast | Simple Q&A, FAQs, greetings |
| `qwen-plus` | Medium & balanced | Most everyday tasks |
| `qwen3.7-max` | Large & powerful | Complex analysis, debugging, creative writing |

It's like hiring staff:
- 🟢 **Flash** = An intern. Cheap, quick, handles routine stuff.
- 🟡 **Plus** = A mid-level employee. Does most jobs well.
- 🔴 **Max** = A senior specialist. You call them only for hard problems.

You wouldn't call your senior specialist to answer "what are your business hours?" — that wastes their time and your money. TokenTrim makes this decision automatically.

---

## 🔌 What is an API?

**API** stands for **Application Programming Interface**. 

The simplest way to think about it: it's a **waiter** at a restaurant.

- You (your app) = the customer
- The AI model = the kitchen
- The API = the waiter who carries your order to the kitchen and brings the food back

You don't go directly into the kitchen. You tell the waiter what you want, and they come back with the result.

In code, calling an AI API looks like this:

```python
response = ai_client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)
print(response.choices[0].message.content)
# Output: "The capital of France is Paris."
```

You send a request. The API charges you tokens. You get a response back.

---

## 🏢 What is Alibaba Cloud Model Studio?

**Model Studio** is Alibaba Cloud's platform for hosting and serving AI models — specifically the **Qwen** family of models.

Think of it as the restaurant itself. It:
- Hosts multiple AI models (`qwen3.5-flash`, `qwen-plus`, `qwen3.7-max`)
- Gives you an **API key** (like a credit card) to authenticate your requests
- Charges you per token used
- Provides embeddings (more on this in Layer 1)
- Has a **free tier** — 1 million free tokens per eligible model for new accounts (Singapore region)

---

## 🔑 What is an API Key?

An API key is a secret string of text that identifies YOU as the person making requests. It looks like this:

```
sk-abc1234xyz567def890...
```

Every request you make to Model Studio includes this key. It's how Alibaba knows:
- Who is making the request
- Which account to charge

> ⚠️ **NEVER share your API key publicly or commit it to GitHub.** Anyone with your key can use it and you'll pay the bill.

In TokenTrim, the key is stored in a `.env` file:
```
DASHSCOPE_API_KEY="sk-your-key-here"
```

---

## 🧲 What are Embeddings? (Important for Later)

This is a concept used heavily in TokenTrim's caching layer.

Imagine you could convert any piece of text into a list of 768 numbers:
- `"Hello, how are you?"` → `[0.23, -0.41, 0.89, 0.12, ..., 0.77]`
- `"Hi, what's up?"` → `[0.24, -0.40, 0.91, 0.11, ..., 0.75]`

These numbers (called a **vector** or **embedding**) capture the *meaning* of the text.

Notice how both sentences above — which mean the same thing — produce **very similar numbers**? That's the magic.

You can mathematically measure how similar two embeddings are, and that tells you how similar the original texts are in **meaning** — even if the exact words are different.

`text-embedding-v4` is Alibaba's model that converts text into these 768-number vectors. TokenTrim uses it to find semantically similar questions that have already been answered.

---

## ✅ Key Takeaways

| Concept | What it is |
|---|---|
| LLM | A large AI model that understands and generates text |
| API | The interface/waiter you use to send requests to the model |
| API Key | Your secret ID/password for billing |
| Model Studio | Alibaba's platform hosting the Qwen models |
| Embedding | Converting text to a list of numbers that represent meaning |

---

➡️ **Next: [03 — The Problem TokenTrim Solves](./03_the_problem_tokentrim_solves.md)**

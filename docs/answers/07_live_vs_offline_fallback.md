# 7. Live vs. Offline Seamless Fallback

## How the Automatic Detection Works

The system uses a **probe-and-fallback** strategy at startup:

### Detection Logic

```
Can we import the `openai` package?
       ├── NO → Use offline providers
       └── YES
            ↓
       Is DASHSCOPE_API_KEY set and non-empty?
       ├── NO → Use offline providers
       └── YES
            ↓
       Is TOKENTRIM_OFFLINE=1 set?
       ├── YES → Force offline mode (developer override)
       └── NO → Use live providers
```

### What "Offline Providers" Means

| Component | Live Provider | Offline Provider |
|-----------|--------------|-----------------|
| Embeddings | [`QwenEmbeddingProvider`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py#L74-L97) — calls `text-embedding-v4` API | [`HashingEmbeddingProvider`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/embeddings.py#L43-L71) — deterministic local hashing |
| Chat Model | [`QwenChatModel`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/qwen_client.py#L36-L61) — calls Qwen API | [`FakeChatModel`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/qwen_client.py#L64-L79) — returns canned response |
| Vector Store | [`PgVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L80-L117) — PostgreSQL + pgvector | [`InMemoryVectorStore`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/cache.py#L51-L77) — Python list with brute-force search |

### Why This Works Seamlessly

The key architectural decision is **dependency injection through Protocol classes**:

```python
# These are abstract interfaces (Protocols)
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> List[float]: ...

class ChatModel(Protocol):
    def generate(self, model: str, messages: ...) -> ChatResult: ...

class VectorStore(Protocol):
    def add(self, query, response, embedding) -> None: ...
    def nearest(self, embedding) -> Optional[Tuple[StoredEntry, float]]: ...
```

The [`Gateway`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/pipeline.py#L41-L52) class accepts **any** object that satisfies these interfaces. It does not know whether it is talking to a real API or a local fake. The fallback is invisible to the pipeline logic.

## The No-Crash Guarantee

### Scenario: Internet Drops Mid-Demo

```
Demo is running with live providers
       ↓
Internet connection drops
       ↓
Next API call to Qwen fails (ConnectionError)
       ↓
WITHOUT fallback: Application crashes, dashboard shows error
       ↓
WITH fallback: System catches the error, switches to offline
  providers, dashboard continues showing data
```

### How to Implement the Mid-Session Fallback

The current implementation selects providers at startup. For a true no-crash guarantee during a live session, a **retry-with-fallback** wrapper is needed:

```python
class ResilientChatModel:
    def __init__(self, live: QwenChatModel, fallback: FakeChatModel):
        self.live = live
        self.fallback = fallback

    def generate(self, model, messages):
        try:
            return self.live.generate(model, messages)
        except Exception:
            return self.fallback.generate(model, messages)
```

This ensures that even a transient API failure during the demo does not crash the system.

## Why This Matters for the Hackathon

| Risk | Without Fallback | With Fallback |
|------|-----------------|---------------|
| Venue Wi-Fi drops | Demo crashes | Demo continues with offline data |
| API key rate-limited | 500 error on screen | Seamless switch to fake responses |
| Postgres unreachable | Cache lookup throws exception | In-memory store takes over |
| Demo at 2 AM, servers under maintenance | Broken demo | Works perfectly offline |

The judges see a system that is **resilient by design**, not one that breaks under real-world conditions. This demonstrates engineering maturity beyond a simple prototype.

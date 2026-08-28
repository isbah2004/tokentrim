# 2. Automated Testing and CI/CD

## The Core Idea

The fundamental principle is:

> **Write the tests once. After that, the system validates itself on every change.**

Manual testing is error-prone, slow, and does not scale. When a developer changes the routing logic in [`router.py`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/app/router.py), they should not have to manually verify that the cache, compressor, and pipeline still work correctly. The automated test suite handles this.

## How the Trigger Model Works

```
Developer edits code
       ↓
git commit + git push
       ↓
CI/CD platform detects the push (webhook trigger)
       ↓
Pipeline starts:
  1. Install dependencies (requirements.txt)
  2. Run linters / static analysis
  3. Run: python -m unittest discover -s tests -t .
  4. If all tests pass → build Docker image
  5. Deploy (staging or production)
       ↓
Developer gets pass/fail notification
```

### The Trigger Mechanism

The "trigger" is a **webhook** configured on the Git hosting platform (GitHub, GitLab, Bitbucket). When a push event occurs on a target branch, the CI/CD platform (GitHub Actions, GitLab CI, Jenkins, etc.) automatically:

1. Spins up a clean environment (container or VM).
2. Checks out the code at the pushed commit.
3. Executes the defined pipeline stages.

### What Gets Tested Automatically

For TokenTrim, the test suite (run via `python -m unittest discover -s tests -t .`) currently validates:

| Test Area | What It Proves |
|-----------|---------------|
| **Cache mechanics** | A first request generates a response; a second identical request is a free cache hit |
| **Routing determinism** | Simple queries → Flash, complex queries → Max, always repeatable |
| **Compression** | History trimming reduces token count, RAG reranking keeps only top-k chunks |
| **Pipeline end-to-end** | The full `cache → compress → route → generate → log` flow works |
| **Offline mode** | Everything runs without network, API keys, or a database |
| **Config validation** | Invalid thresholds or missing pricing entries are caught before runtime |

### Why This Solves the Manual Testing Problem

Without automation:
- A developer changes `THRESHOLD_FLASH` from `0.35` to `0.40`.
- They forget to test whether borderline queries now route to a different model.
- The demo breaks in front of judges.

With automation:
- The same change triggers the pipeline.
- The routing unit tests immediately fail if any query's expected model assignment changes.
- The developer is notified **before** the code reaches production.

### Example CI/CD Configuration (GitHub Actions)

```yaml
name: TokenTrim CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m unittest discover -s tests -t .
```

This ensures that **every push** and **every pull request** runs the full test suite. No manual intervention required.

# 5. Git and CI/CD Workflow

## The Automated Workflow

The goal is to eliminate manual validation steps between writing code and deploying it. The workflow is:

```
Developer makes changes (local machine)
       ↓
git add + git commit
       ↓
git push origin <branch>
       ↓
Git platform (GitHub/GitLab) receives push
       ↓
Webhook triggers CI/CD pipeline
       ↓
Pipeline stages execute in order:
  ┌─────────────────────────────────┐
  │ 1. Checkout code                │
  │ 2. Install dependencies         │
  │ 3. Run linters (flake8, mypy)   │
  │ 4. Run unit tests               │
  │ 5. Run integration tests        │
  │ 6. Build Docker image            │
  │ 7. Push image to registry       │
  │ 8. Deploy to staging            │
  │ 9. (Optional) Deploy to prod    │
  └─────────────────────────────────┘
       ↓
Pass/Fail notification to developer
```

## How This Applies to TokenTrim

### Stage 1: Tests

```bash
# The existing test command
python -m unittest discover -s tests -t .
# Expected: 53 tests pass, 3 skipped
```

This validates every layer:
- **Layer 1** (Cache): Semantic cache hit/miss logic
- **Layer 2** (Compressor): History trimming and RAG reranking
- **Layer 3** (Router): Model selection based on difficulty score
- **Pipeline**: Full end-to-end `cache → compress → route → generate → log` flow

### Stage 2: Build

```bash
docker-compose build
```

Uses the existing [`docker-compose.yml`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/docker-compose.yml) to build the application container with Postgres/pgvector.

### Stage 3: Deploy

For the hackathon, deployment could target:
- Alibaba Cloud ECS (Elastic Compute Service)
- A simple VPS with Docker
- A local machine for the live demo

## Why Automation Matters

| Without CI/CD | With CI/CD |
|---------------|------------|
| Developer pushes broken code | Broken code is caught by tests before merge |
| Nobody notices until the demo | Immediate notification with failure details |
| Manual testing takes 30+ minutes | Automated tests run in < 2 minutes |
| "It worked on my machine" | Runs in a clean, reproducible environment |
| Fear of making changes | Confidence to refactor and improve |

## The Key Principle

> **Once automated tests are properly implemented, every future change is automatically validated.**

This is not just about the hackathon. It is about building a system where the team can iterate quickly and confidently. The test suite (which already exists in the [`tests/`](file:///Users/syedisbah/Documents/ZyphramProjects/token_optimizer/tests) directory) is the foundation. CI/CD simply ensures those tests run on every change, automatically, without anyone needing to remember to run them.

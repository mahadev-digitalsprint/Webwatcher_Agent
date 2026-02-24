# Architecture V1

This repository implements a deterministic-first Financial IR Monitoring Intelligence Engine.

Key design points:

- Immutable snapshots with normalized structured content
- Incremental crawl and deduplicated traversal
- Deterministic financial extraction with optional LLM fallback
- Rule-based materiality and confidence scoring
- Celery + Redis orchestration with distributed lock
- FastAPI operational APIs for company/run/change workflows

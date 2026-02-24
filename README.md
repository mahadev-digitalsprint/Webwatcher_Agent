# Webwatcher_Agent

Financial IR Monitoring & Intelligence System.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -e .[dev]`
3. Copy env template:
   - `cp .env.example .env`
4. Run API:
   - `uvicorn webwatcher.app:app --reload --host 0.0.0.0 --port 8080`
5. Run Celery worker:
   - `celery -A webwatcher.orchestration.queue.celery_app worker -l info -Q crawl,pdf,extract,diff,alerts,scheduler`
6. Run Celery beat:
   - `celery -A webwatcher.orchestration.queue.celery_app beat -l info`

Redis default is configured for container networking as `redis://redis:6379/0`.
For direct local Redis service usage, set `REDIS_URL=redis://localhost:6379/0`.

## Architecture

The codebase is organized by layers:

- `core/`: config, db session, logging
- `crawler/`: fetch, crawl controller, IR discovery
- `normalization/`: HTML normalization and URL canonicalization
- `storage/`: snapshot logic and blob archival
- `pdf/`: document monitor and parser
- `financial/`: deterministic financial extraction and unit mapping
- `llm/`: Azure OpenAI wrappers and validation helpers
- `intelligence/`: change detection, materiality, confidence
- `orchestration/`: scheduler + monitor worker
- `api/`: company/monitor/changes routes
- `observability/`: metrics helpers
- `tests/`: unit and integration tests

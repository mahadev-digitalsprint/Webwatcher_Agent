from celery import Celery
from celery.schedules import crontab

from webwatcher.core.config import get_settings

settings = get_settings()

celery_app = Celery("webwatcher", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone="UTC",
    task_acks_late=True,
    task_default_queue="crawl",
    worker_concurrency=settings.celery_concurrency,
    task_routes={
        "webwatcher.orchestration.scheduler.tick_scheduler": {"queue": "scheduler"},
        "webwatcher.orchestration.monitor_worker.run_monitor_task": {"queue": "crawl"},
    },
    beat_schedule={
        "tick-scheduler-every-5-mins": {
            "task": "webwatcher.orchestration.scheduler.tick_scheduler",
            "schedule": crontab(minute="*/5"),
        }
    },
)
celery_app.autodiscover_tasks(["webwatcher.orchestration"])

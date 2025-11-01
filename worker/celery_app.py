"""
Celery Application Configuration for Part 1 Async Processing.

Celery is used ONLY for Part 1 (transaction monitoring) to enable high-throughput
async processing. Part 2 (document corroboration) does NOT use Celery.
"""

import logging

from celery import Celery
from config import settings

logger = logging.getLogger(__name__)

# Resolve broker/backend URLs as plain strings (Celery/Kombu expect str)
broker_url = None
backend_url = None

# Prefer dedicated CELERY_* settings when available, else fall back to REDIS_URL
try:
    broker_url = str(getattr(settings, "celery_broker_url", None) or settings.redis_url)
except Exception:
    broker_url = str(settings.redis_url)

try:
    backend_url = str(getattr(settings, "celery_result_backend", None) or settings.redis_url)
except Exception:
    backend_url = str(settings.redis_url)

# Create Celery app
celery_app = Celery(
    "slenth_aml",
    broker=broker_url,
    backend=backend_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
)

logger.info("Celery app initialized")

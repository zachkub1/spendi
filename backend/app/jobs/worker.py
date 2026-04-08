"""
Celery worker configuration for background jobs.
Handles email sync, transaction processing, and scheduled tasks.
"""
from celery import Celery
from celery.schedules import crontab
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    'ledgerly',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.jobs.tasks']  # Import task modules
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minute soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Scheduled tasks (periodic)
celery_app.conf.beat_schedule = {
    'sync-all-email-accounts-hourly': {
        'task': 'app.jobs.tasks.sync_all_email_accounts',
        'schedule': crontab(minute=0),  # Every hour at minute 0
    },
    # Add more scheduled tasks here as needed
}

logger.info("Celery worker initialized")

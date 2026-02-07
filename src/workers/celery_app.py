"""
Celery Application Configuration

Configures Celery for async task processing.
"""

from celery import Celery
from celery.schedules import crontab

from src.config import settings


# Create Celery app
celery_app = Celery(
    "support_router",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Rate limiting
    task_default_rate_limit="100/m",
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Routing
    task_routes={
        "src.workers.tasks.process_ticket_task": {"queue": "tickets"},
        "src.workers.tasks.sync_external_ticket_task": {"queue": "sync"},
        "src.workers.tasks.send_notification_task": {"queue": "notifications"},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Reset daily agent stats at midnight
        "reset-daily-stats": {
            "task": "src.workers.tasks.reset_daily_stats_task",
            "schedule": crontab(hour=0, minute=0),
        },
        # Check for SLA breaches every 5 minutes
        "check-sla-breaches": {
            "task": "src.workers.tasks.check_sla_breaches_task",
            "schedule": crontab(minute="*/5"),
        },
        # Sync external systems every 10 minutes
        "sync-external-systems": {
            "task": "src.workers.tasks.sync_external_systems_task",
            "schedule": crontab(minute="*/10"),
        },
    }
)


# Task base class with error handling
class TaskBase:
    """Base class for tasks with common error handling."""
    
    abstract = True
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

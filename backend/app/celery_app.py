"""Celery application wiring for background care plan generation."""

import logging
import os

from celery import Celery
from celery.signals import worker_ready

logger = logging.getLogger(__name__)


def get_celery_broker_url() -> str:
    """Return the Redis URL Celery uses for task transport."""
    return os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")


def get_celery_result_backend() -> str:
    """Return the Redis URL Celery uses for task state/results."""
    return os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")


celery_app = Celery(
    "careplan_generator",
    broker=get_celery_broker_url(),
    backend=get_celery_result_backend(),
    include=["app.tasks.care_plan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Acknowledge tasks after successful execution, not as soon as received.
    task_acks_late=True,
    # Requeue/reject a task if the worker child process dies mid-execution.
    task_reject_on_worker_lost=True,
    # Avoid one worker reserving too many tasks while others sit idle.
    worker_prefetch_multiplier=1,
)


@worker_ready.connect
def log_worker_ready(**kwargs) -> None:
    """Log when the Celery worker is ready to receive jobs."""
    logger.info("Celery care plan worker ready")

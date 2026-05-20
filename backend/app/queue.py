"""Redis-backed dispatch queue for care plan generation jobs."""

import os

from redis import Redis

def get_redis_url() -> str:
    """Return the configured Redis URL for queue dispatch."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_care_plan_queue_name() -> str:
    """Return the Redis list name used for care plan job references."""
    return os.getenv("CARE_PLAN_QUEUE_NAME", "care_plan_jobs")


def enqueue_care_plan_job(order_id: str) -> None:
    """Push only an order id into Redis for future worker processing."""
    redis_client = Redis.from_url(get_redis_url(), decode_responses=True)
    redis_client.rpush(get_care_plan_queue_name(), order_id)

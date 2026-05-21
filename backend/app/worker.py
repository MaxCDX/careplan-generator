"""Minimal Day 5 Redis worker for queued care plan generation."""

import logging
import os
import time

from redis import Redis

from app.care_plans import repository as care_plan_repository
from app.care_plans.routes import generate_care_plan_content
from app.database import SessionLocal
from app.orders.models import Order
from app.queue import get_care_plan_queue_name, get_redis_url

logger = logging.getLogger(__name__)

WORKER_FAILURE_MESSAGE = "Care plan generation failed. Please try again later."
WORKER_BLPOP_TIMEOUT_SECS = 5


def get_openai_model() -> str:
    """Return the model name used for worker-side care plan generation."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_worker_max_attempts() -> int:
    """Return how many times the manual worker should try generation."""
    return int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))


def get_worker_retry_delay_secs() -> int:
    """Return how long the manual worker waits between failed attempts."""
    return int(os.getenv("WORKER_RETRY_DELAY_SECS", "5"))


def process_order(order_id: str) -> None:
    """Process one queued order id and persist the resulting workflow state."""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).one_or_none()
        if not order:
            logger.warning("Skipping care plan job because order was not found: %s", order_id)
            return

        if order.status != "queued":
            logger.info(
                "Skipping care plan job for order %s because status is %s",
                order_id,
                order.status,
            )
            return

        order.status = "processing"
        order.error_message = None
        db.add(order)
        db.commit()
        db.refresh(order)
        logger.info("Order %s moved to processing", order_id)

        model = get_openai_model()
        max_attempts = get_worker_max_attempts()
        retry_delay_secs = get_worker_retry_delay_secs()
        for attempt in range(1, max_attempts + 1):
            logger.info(
                "Starting care plan generation attempt %s/%s for order %s",
                attempt,
                max_attempts,
                order_id,
            )
            try:
                care_plan_content = generate_care_plan_content(order, model)
                care_plan_repository.create_care_plan(
                    db,
                    order=order,
                    care_plan_content=care_plan_content,
                    model=model,
                )

                order.status = "completed"
                order.error_message = None
                db.add(order)
                db.commit()
                logger.info("Completed care plan generation for order %s", order_id)
                return
            except Exception:
                db.rollback()
                logger.exception(
                    "Care plan generation attempt %s/%s failed for order %s",
                    attempt,
                    max_attempts,
                    order_id,
                )
                if attempt < max_attempts:
                    logger.info(
                        "Retrying order %s after %s seconds",
                        order_id,
                        retry_delay_secs,
                    )
                    time.sleep(retry_delay_secs)
                    continue

                logger.error("Final care plan generation attempt failed for order %s", order_id)
                order.status = "failed"
                order.error_message = WORKER_FAILURE_MESSAGE
                db.add(order)
                db.commit()
    finally:
        db.close()


def worker_loop() -> None:
    """Block on Redis for order ids and process jobs one at a time."""
    redis_client = Redis.from_url(get_redis_url(), decode_responses=True)
    queue_name = get_care_plan_queue_name()
    logger.info("Care plan worker starting")
    logger.info("Care plan worker listening on Redis queue %s", queue_name)

    while True:
        try:
            job = redis_client.blpop(queue_name, timeout=WORKER_BLPOP_TIMEOUT_SECS)
            if job is None:
                continue

            _, order_id = job
            logger.info("Received care plan job for order %s", order_id)
            process_order(order_id)
        except Exception:
            logger.exception("Worker loop recovered from an unexpected error")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker_loop()

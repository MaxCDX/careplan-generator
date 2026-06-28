"""Celery tasks for asynchronous care plan generation."""

import logging
import os

from app.care_plans import repository as care_plan_repository
from app.care_plans.service import generate_care_plan_content
from app.celery_app import celery_app
from app.database import SessionLocal
from app.llm.errors import LLMConfigurationError
from app.orders.models import Order

logger = logging.getLogger(__name__)

WORKER_FAILURE_MESSAGE = "Care plan generation failed. Please try again later."
MAX_RETRIES = 3


def get_llm_model() -> str:
    """Return the configured model, with legacy OpenAI fallback support."""
    return (
        os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    )


def get_retry_countdown(retry_count: int) -> int:
    """Return a small exponential backoff delay for the next Celery retry."""
    return 2**retry_count


def process_order_for_celery(task_self, order_id: str) -> dict[str, str]:
    """Process one order id inside a Celery task-owned DB session."""
    db = SessionLocal()
    try:
        logger.info("Care plan task received for order %s", order_id)
        order = db.query(Order).filter(Order.id == order_id).one_or_none()
        if not order:
            logger.warning("Skipping care plan task because order was not found: %s", order_id)
            return {"status": "order_not_found", "order_id": order_id}

        can_process_order = order.status == "queued" or (
            order.status == "processing" and task_self.request.retries > 0
        )
        if not can_process_order:
            logger.info(
                "Skipping care plan task for order %s because status is %s",
                order_id,
                order.status,
            )
            return {"status": "skipped", "order_id": order_id}

        if order.status == "queued":
            order.status = "processing"
            order.error_message = None
            db.add(order)
            db.commit()
            db.refresh(order)
            logger.info("Order %s moved to processing", order_id)

        try:
            model = get_llm_model()
            logger.info(
                "Starting care plan generation for order %s, retry %s/%s",
                order_id,
                task_self.request.retries,
                MAX_RETRIES,
            )
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
            return {"status": "completed", "order_id": order_id}
        except LLMConfigurationError:
            db.rollback()
            logger.exception("Care plan generation configuration error for order %s", order_id)
            order.status = "failed"
            order.error_message = WORKER_FAILURE_MESSAGE
            db.add(order)
            db.commit()
            raise
        except Exception as exc:
            db.rollback()
            if task_self.request.retries < MAX_RETRIES:
                countdown = get_retry_countdown(task_self.request.retries)
                logger.exception(
                    "Care plan generation failed for order %s; retrying in %s seconds",
                    order_id,
                    countdown,
                )
                raise task_self.retry(exc=exc, countdown=countdown)

            logger.exception("Final care plan generation failure for order %s", order_id)
            order.status = "failed"
            order.error_message = WORKER_FAILURE_MESSAGE
            db.add(order)
            db.commit()
            return {"status": "failed", "order_id": order_id}
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.care_plan_tasks.generate_care_plan_task", max_retries=MAX_RETRIES)
def generate_care_plan_task(self, order_id: str) -> dict[str, str]:
    """Celery entrypoint for generating a care plan from an order id only."""
    return process_order_for_celery(self, order_id)

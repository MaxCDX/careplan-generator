"""Order workflow business logic."""

import logging

from sqlalchemy.orm import Session

from app.orders import repository
from app.orders.models import Order
from app.orders.schemas import OrderCreate
from app.tasks.care_plan_tasks import generate_care_plan_task

DISPATCH_FAILURE_MESSAGE = "Failed to enqueue care plan generation request."


class OrderDispatchError(Exception):
    """Raised when a persisted order cannot be dispatched to the worker."""


def create_order_and_dispatch_care_plan(db: Session, data: OrderCreate) -> Order:
    """Create a queued Order and dispatch its id to the Celery worker."""
    order = repository.create_order(db, data)

    try:
        generate_care_plan_task.delay(order.id)
    except Exception as exc:
        logging.exception("Care plan Celery dispatch failed for order %s", order.id)
        try:
            repository.mark_order_failed(db, order.id, DISPATCH_FAILURE_MESSAGE)
        except Exception:
            logging.exception("Failed to persist Celery dispatch failure state for order %s", order.id)
        raise OrderDispatchError from exc

    return order

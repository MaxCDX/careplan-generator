import logging
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.care_plans import repository as care_plan_repository
from app.care_plans.schemas import CarePlanGenerateRequest, CarePlanRead
from app.care_plans.serializers import serialize_care_plan
from app.care_plans.service import generate_care_plan_content
from app.database import get_db
from app.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.llm.errors import LLMConfigurationError, LLMProviderError
from app.orders import repository as order_repository

router = APIRouter(prefix="/care-plans", tags=["care-plans"])
SAFE_GENERATION_ERROR_MESSAGE = "Care plan generation failed. Please try again later."


def _mark_order_generation_failed(db: Session, order) -> None:
    """Persist a safe failed state without exposing the underlying exception."""
    db.rollback()
    order.status = "failed"
    order.error_message = SAFE_GENERATION_ERROR_MESSAGE
    db.add(order)
    db.commit()


@router.post("", response_model=CarePlanRead)
def generate_care_plan(data: CarePlanGenerateRequest, db: Session = Depends(get_db)):
    """Directly generate and persist a CarePlan for an existing Order.

    This compatibility path is superseded by the Celery-based async Order
    workflow used by POST /orders.
    """
    order = order_repository.get_order(db, data.order_id)
    if not order:
        raise NotFoundError(
            code="ORDER_NOT_FOUND",
            message="Order not found.",
        )
    if order.care_plan:
        raise ConflictError(
            code="CARE_PLAN_ALREADY_EXISTS",
            message="Care plan already exists for this order.",
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Order owns workflow status; CarePlan is only the generated artifact.
    order.status = "processing"
    order.error_message = None
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        logging.info("Starting LLM call for order %s", order.id)
        care_plan_content = generate_care_plan_content(order, model)
    except (LLMConfigurationError, LLMProviderError) as exc:
        _mark_order_generation_failed(db, order)
        raise ServiceUnavailableError(
            code="CARE_PLAN_GENERATION_UNAVAILABLE",
            message="Care plan generation is currently unavailable. Please try again later.",
        ) from exc
    except Exception:
        _mark_order_generation_failed(db, order)
        raise

    try:
        # Persist generated content only after the LLM call succeeds.
        care_plan = care_plan_repository.create_care_plan(
            db,
            order=order,
            care_plan_content=care_plan_content,
            model=model,
        )
        order.status = "completed"
        order.error_message = None
        db.add(order)
        db.commit()
        logging.info("LLM call completed for order %s", order.id)
        return serialize_care_plan(care_plan)
    except Exception:
        _mark_order_generation_failed(db, order)
        raise


@router.get("", response_model=list[CarePlanRead])
def list_care_plans(db: Session = Depends(get_db)):
    """Return all persisted generated care plans, newest first."""
    return [serialize_care_plan(care_plan) for care_plan in care_plan_repository.list_care_plans(db)]


@router.get("/{care_plan_id}", response_model=CarePlanRead)
def get_care_plan(care_plan_id: str, db: Session = Depends(get_db)):
    """Return one generated CarePlan by id."""
    care_plan = care_plan_repository.get_care_plan(db, care_plan_id)
    if not care_plan:
        raise NotFoundError(
            code="CARE_PLAN_NOT_FOUND",
            message="Care plan not found.",
        )
    return serialize_care_plan(care_plan)

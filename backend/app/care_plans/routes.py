import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.care_plans import repository as care_plan_repository
from app.care_plans.schemas import CarePlanGenerateRequest, CarePlanRead
from app.care_plans.service import generate_care_plan_content
from app.database import get_db
from app.care_plans.models import CarePlan
from app.orders import repository as order_repository

router = APIRouter(prefix="/care-plans", tags=["care-plans"])


def serialize_care_plan(care_plan: CarePlan) -> CarePlanRead:
    """Convert a CarePlan SQLAlchemy model into the public API response."""
    return CarePlanRead(
        id=care_plan.id,
        order_id=care_plan.order_id,
        model=care_plan.model,
        care_plan=care_plan.care_plan_content,
        created_at=care_plan.created_at,
    )


@router.post("", response_model=CarePlanRead)
def generate_care_plan(data: CarePlanGenerateRequest, db: Session = Depends(get_db)):
    """Directly generate and persist a CarePlan for an existing Order.

    This compatibility path is superseded by the Celery-based async Order
    workflow used by POST /orders.
    """
    order = order_repository.get_order(db, data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.care_plan:
        raise HTTPException(status_code=409, detail="Care plan already exists for this order")

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
    except Exception as exc:
        db.rollback()
        # Keep failed generation state durable so a restart does not erase it.
        order.status = "failed"
        order.error_message = str(getattr(exc, "detail", exc))[:1000]
        db.add(order)
        db.commit()
        raise HTTPException(
            status_code=getattr(exc, "status_code", 500),
            detail=f"Care plan generation failed: {getattr(exc, 'detail', exc)}",
        ) from exc


@router.get("", response_model=list[CarePlanRead])
def list_care_plans(db: Session = Depends(get_db)):
    """Return all persisted generated care plans, newest first."""
    return [serialize_care_plan(care_plan) for care_plan in care_plan_repository.list_care_plans(db)]


@router.get("/{care_plan_id}", response_model=CarePlanRead)
def get_care_plan(care_plan_id: str, db: Session = Depends(get_db)):
    """Return one generated CarePlan by id."""
    care_plan = care_plan_repository.get_care_plan(db, care_plan_id)
    if not care_plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    return serialize_care_plan(care_plan)

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.orders.models import Order
from app.orders import repository
from app.orders.schemas import OrderAccepted, OrderCreate, OrderRead
from app.patients.schemas import PatientRead
from app.providers.schemas import ProviderRead
from app.queue import enqueue_care_plan_job

router = APIRouter(prefix="/orders", tags=["orders"])

QUEUE_FAILURE_MESSAGE = "Failed to enqueue care plan generation request."


def serialize_order(order: Order) -> OrderRead:
    """Convert a loaded Order SQLAlchemy model into the public API response."""
    return OrderRead(
        id=order.id,
        patient=PatientRead(
            id=order.patient.id,
            name=order.patient.name,
            mrn=order.patient.mrn,
            dob=order.patient.dob,
        ),
        provider=ProviderRead(
            id=order.provider.id,
            name=order.provider.name,
            npi=order.provider.npi,
        ),
        medication=order.medication,
        diagnosis=order.diagnosis,
        clinical_notes=order.clinical_notes,
        status=order.status,
        error_message=order.error_message,
        has_care_plan=order.care_plan is not None,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("", response_model=OrderAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """Create a queued Order and dispatch its id for future background generation."""
    order = repository.create_order(db, data)

    try:
        enqueue_care_plan_job(order.id)
    except Exception as exc:
        logging.exception("Care plan queue dispatch failed for order %s", order.id)
        try:
            repository.mark_order_failed(db, order.id, QUEUE_FAILURE_MESSAGE)
        except Exception:
            logging.exception("Failed to persist queue failure state for order %s", order.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Care plan request could not be queued. Please try again later.",
        ) from exc

    return OrderAccepted(
        order_id=order.id,
        status="queued",
        message="Care plan generation request accepted",
    )


@router.get("", response_model=list[OrderRead])
def list_orders(db: Session = Depends(get_db)):
    """Return all persisted Orders, newest first."""
    return [serialize_order(order) for order in repository.list_orders(db)]


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Return one persisted Order by id, including linked patient/provider data."""
    order = repository.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(order)

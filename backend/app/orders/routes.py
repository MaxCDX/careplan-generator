from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.orders.models import Order
from app.orders import repository
from app.orders import service
from app.orders.schemas import OrderAccepted, OrderCreate, OrderRead, OrderStatusRead
from app.patients.schemas import PatientRead
from app.providers.schemas import ProviderRead

router = APIRouter(prefix="/orders", tags=["orders"])


def serialize_order(order: Order) -> OrderRead:
    """Convert a loaded Order SQLAlchemy model into the public API response."""
    care_plan_content = (
        order.care_plan.care_plan_content
        if order.status == "completed" and order.care_plan is not None
        else None
    )

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
        care_plan_content=care_plan_content,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def serialize_order_status(order: Order) -> OrderStatusRead:
    """Convert an Order into the minimal Day 6 polling response."""
    care_plan_content = (
        order.care_plan.care_plan_content
        if order.status == "completed" and order.care_plan is not None
        else None
    )

    return OrderStatusRead(
        id=order.id,
        status=order.status,
        error_message=order.error_message,
        has_care_plan=order.care_plan is not None,
        care_plan_content=care_plan_content,
    )


@router.post("", response_model=OrderAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """Create a queued Order and dispatch its id to the Celery worker."""
    try:
        order = service.create_order_and_dispatch_care_plan(db, data)
    except service.OrderDispatchError as exc:
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


@router.get("/{order_id}/status", response_model=OrderStatusRead)
def get_order_status(order_id: str, db: Session = Depends(get_db)):
    """Return minimal order workflow state for frontend polling."""
    order = repository.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order_status(order)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Return one persisted Order by id, including linked patient/provider data."""
    order = repository.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(order)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.orders.models import Order
from app.orders import repository
from app.orders.schemas import OrderCreate, OrderRead
from app.patients.schemas import PatientRead
from app.providers.schemas import ProviderRead

router = APIRouter(prefix="/orders", tags=["orders"])


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


@router.post("", response_model=OrderRead)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """Create a durable Order workflow record from validated request data."""
    order = repository.create_order(db, data)
    return serialize_order(order)


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

from sqlalchemy.orm import Session, joinedload

from app.orders.models import Order
from app.orders.schemas import OrderCreate
from app.patients.repository import get_or_create_patient
from app.providers.repository import get_or_create_provider


def create_order(db: Session, data: OrderCreate) -> Order:
    """Create a durable queued order workflow record from validated API input.

    Reuses existing Patient/Provider rows when MRN/NPI already exist.
    Returns the persisted Order with related Patient/Provider loaded.
    """
    patient = get_or_create_patient(db, name=data.patient_name, mrn=data.mrn, dob=data.patient_dob)
    provider = get_or_create_provider(db, name=data.provider_name, npi=data.provider_npi)

    # Order owns workflow state; CarePlan is created only after generation succeeds.
    order = Order(
        patient_id=patient.id,
        provider_id=provider.id,
        medication=data.medication,
        diagnosis=data.diagnosis,
        clinical_notes=data.clinical_notes,
        status="queued",
    )
    db.add(order)
    db.commit()
    return get_order(db, order.id)  # type: ignore[return-value]


def get_latest_order_for_patient_and_medication(db: Session, *, patient_id: str, medication: str) -> Order | None:
    """Return newest Order for a patient and medication."""
    return (
        db.query(Order)
        .filter(Order.patient_id == patient_id, Order.medication == medication)
        .order_by(Order.created_at.desc())
        .first()
    )


def mark_order_failed(db: Session, order_id: str, error_message: str) -> None:
    """Persist a safe failed state when dispatch cannot be completed."""
    order = db.query(Order).filter(Order.id == order_id).one_or_none()
    if not order:
        return

    order.status = "failed"
    order.error_message = error_message[:1000]
    db.add(order)
    db.commit()


def list_orders(db: Session) -> list[Order]:
    """Load all Orders with related rows needed by the API serializer."""
    return (
        db.query(Order)
        .options(joinedload(Order.patient), joinedload(Order.provider), joinedload(Order.care_plan))
        .order_by(Order.created_at.desc())
        .all()
    )


def get_order(db: Session, order_id: str) -> Order | None:
    """Load one Order by id with Patient, Provider, and optional CarePlan."""
    return (
        db.query(Order)
        .options(joinedload(Order.patient), joinedload(Order.provider), joinedload(Order.care_plan))
        .filter(Order.id == order_id)
        .one_or_none()
    )

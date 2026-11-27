from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.orders.models import Order
from app.orders.schemas import OrderCreate
from app.patients.repository import full_name_contains, get_or_create_patient
from app.providers.repository import get_or_create_provider


def create_order(db: Session, data: OrderCreate) -> Order:
    """Create a durable queued order workflow record from validated API input.

    Reuses existing Patient/Provider rows when MRN/NPI already exist.
    Returns the persisted Order with related Patient/Provider loaded.
    """
    patient = get_or_create_patient(
        db, first_name=data.patient_first_name, middle_name=data.patient_middle_name,
        last_name=data.patient_last_name, mrn=data.mrn, dob=data.patient_date_of_birth,
    )
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


def list_orders(
    db: Session, *, page: int = 1, page_size: int = 20,
    order_status: str | None = None, patient_name: str | None = None,
    patient_id: str | None = None, provider_id: str | None = None,
) -> tuple[int, list[Order]]:
    """Count matching Orders and load only the requested page with related rows."""
    query = db.query(Order)
    if order_status is not None:
        query = query.filter(Order.status == order_status)
    if patient_id is not None:
        query = query.filter(Order.patient_id == patient_id)
    if provider_id is not None:
        query = query.filter(Order.provider_id == provider_id)
    cleaned_name = patient_name.strip() if patient_name is not None else ""
    if cleaned_name:
        query = query.join(Order.patient).filter(full_name_contains(cleaned_name))

    count = query.count()
    orders = (
        query
        .options(joinedload(Order.patient), joinedload(Order.provider), joinedload(Order.care_plan))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
        .all()
    )
    return count, orders


PREVIEW_LENGTH = 200


def get_status_snapshot(db: Session, order_id: str):
    from app.models import CarePlan

    return (
        db.query(
            Order.id, Order.status, Order.error_message,
            case((Order.status == "completed", func.substr(
                CarePlan.care_plan_content, 1, PREVIEW_LENGTH + 1
            ))).label("preview"),
        )
        .outerjoin(Order.care_plan)
        .filter(Order.id == order_id)
        .one_or_none()
    )


def get_order(db: Session, order_id: str) -> Order | None:
    """Load one Order by id with Patient, Provider, and optional CarePlan."""
    return (
        db.query(Order)
        .options(joinedload(Order.patient), joinedload(Order.provider), joinedload(Order.care_plan))
        .filter(Order.id == order_id)
        .one_or_none()
    )

from app.orders.models import Order
from app.orders.schemas import OrderRead, OrderStatusRead
from app.patients.serializers import serialize_patient
from app.providers.schemas import ProviderRead


def serialize_order(order: Order) -> OrderRead:
    """Convert a loaded Order SQLAlchemy model into the public API response."""
    care_plan_content = (
        order.care_plan.care_plan_content
        if order.status == "completed" and order.care_plan is not None
        else None
    )

    return OrderRead(
        id=order.id,
        patient=serialize_patient(order.patient),
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


def serialize_order_status(order) -> OrderStatusRead:
    from app.orders.repository import PREVIEW_LENGTH

    preview = order.preview
    if preview and len(preview) > PREVIEW_LENGTH:
        preview = preview[:PREVIEW_LENGTH] + "…"
    return OrderStatusRead(
        order_id=order.id,
        status=order.status,
        error_message=order.error_message if order.status == "failed" else None,
        careplan_preview=preview,
    )

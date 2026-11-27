from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError, ServiceUnavailableError
from app.orders import repository
from app.orders import service
from app.orders.serializers import serialize_order, serialize_order_status
from app.orders.schemas import OrderAccepted, OrderCreate, OrderListResponse, OrderRead, OrderStatusRead, WarningResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_200_OK: {
            "model": WarningResponse,
            "description": "Business warning requiring confirmation",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid request input",
        },
        status.HTTP_409_CONFLICT: {
            "description": "Business conflict",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Queue unavailable",
        },
    },
)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """Create a queued Order and dispatch its id to the Celery worker."""
    try:
        order = service.create_order_and_dispatch_care_plan(db, data)
    except service.OrderDispatchError as exc:
        raise ServiceUnavailableError(
            code="CARE_PLAN_QUEUE_UNAVAILABLE",
            message="Care plan request could not be queued. Please try again later.",
        ) from exc

    if isinstance(order, WarningResponse):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=order.model_dump(),
        )

    return OrderAccepted(
        order_id=order.id,
        status="queued",
        message="Care plan generation request accepted",
    )


@router.get(
    "",
    response_model=OrderListResponse,
    responses={400: {"description": "Invalid query parameters"}},
)
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_status: Literal["queued", "processing", "completed", "failed"] | None = Query(default=None, alias="status"),
    patient_name: str | None = Query(default=None),
    patient_id: UUID | None = None,
    provider_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    """Return a filtered page of Orders, newest first."""
    count, orders = repository.list_orders(
        db, page=page, page_size=page_size,
        order_status=order_status, patient_name=patient_name,
        patient_id=str(patient_id) if patient_id is not None else None,
        provider_id=str(provider_id) if provider_id is not None else None,
    )
    return OrderListResponse(
        count=count, page=page, page_size=page_size,
        results=[serialize_order(order) for order in orders],
    )


@router.get("/{order_id}/status", response_model=OrderStatusRead, response_model_exclude_none=True)
def get_order_status(order_id: str, db: Session = Depends(get_db)):
    """Return minimal order workflow state for frontend polling."""
    order = repository.get_status_snapshot(db, order_id)
    if not order:
        raise NotFoundError(
            code="ORDER_NOT_FOUND",
            message="Order not found.",
        )
    return serialize_order_status(order)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Return one persisted Order by id, including linked patient/provider data."""
    order = repository.get_order(db, order_id)
    if not order:
        raise NotFoundError(
            code="ORDER_NOT_FOUND",
            message="Order not found.",
        )
    return serialize_order(order)

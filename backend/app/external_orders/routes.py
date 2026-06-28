from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BadRequestError, ServiceUnavailableError
from app.external_orders.service import normalize_external_order
from app.orders import service as order_service
from app.orders.schemas import OrderAccepted, WarningResponse

router = APIRouter(prefix="/external-orders", tags=["external-orders"])


@router.post(
    "/{source}",
    response_model=OrderAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_200_OK: {
            "model": WarningResponse,
            "description": "Business warning requiring confirmation",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid external order input",
        },
        status.HTTP_409_CONFLICT: {
            "description": "Business conflict",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Queue unavailable",
        },
    },
)
def create_external_order(
    source: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Normalize an external order, then reuse the existing Order workflow."""
    try:
        normalized_order = normalize_external_order(source, payload)
    except (ValueError, ValidationError) as exc:
        raise BadRequestError(
            code="INVALID_EXTERNAL_ORDER",
            message="Invalid external order input.",
            detail={"error": str(exc)},
        ) from exc

    try:
        order = order_service.create_order_and_dispatch_care_plan(db, normalized_order)
    except order_service.OrderDispatchError as exc:
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

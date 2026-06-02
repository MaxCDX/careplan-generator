"""Order workflow business logic."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.exceptions import ConflictError
from app.orders import repository
from app.orders.models import Order
from app.orders.schemas import OrderCreate, WarningResponse
from app.patients import repository as patient_repository
from app.providers import repository as provider_repository
from app.tasks.care_plan_tasks import generate_care_plan_task

DISPATCH_FAILURE_MESSAGE = "Failed to enqueue care plan generation request."


class OrderDispatchError(Exception):
    """Raised when a persisted order cannot be dispatched to the worker."""


def create_order_and_dispatch_care_plan(db: Session, data: OrderCreate) -> Order | WarningResponse:
    """Create a queued Order and dispatch its id to the Celery worker."""
    provider = provider_repository.get_provider_by_npi(db, data.provider_npi)
    if provider and provider.name != data.provider_name:
        raise ConflictError(
            code="PROVIDER_NPI_CONFLICT",
            message="Provider NPI already belongs to a different provider name.",
        )

    patient = patient_repository.get_patient_by_mrn(db, data.mrn)
    warnings = []

    if patient:
        if patient.name != data.patient_name or patient.dob != data.patient_dob:
            warnings.append(
                {
                    "code": "PATIENT_MRN_MISMATCH",
                    "message": "Patient MRN exists but name or DOB is different.",
                }
            )
    elif data.patient_dob:
        same_identity_patient = patient_repository.get_patient_by_name_and_dob(
            db,
            name=data.patient_name,
            dob=data.patient_dob,
        )
        if same_identity_patient and same_identity_patient.mrn != data.mrn:
            warnings.append(
                {
                    "code": "PATIENT_POSSIBLE_DUPLICATE",
                    "message": "Patient name and DOB already exist with a different MRN.",
                }
            )

    if patient:
        existing_order = repository.get_latest_order_for_patient_and_medication(
            db,
            patient_id=patient.id,
            medication=data.medication,
        )
        if existing_order:
            if existing_order.created_at.date() == datetime.now().date():
                raise ConflictError(
                    code="DUPLICATE_ORDER_SAME_DAY",
                    message="Duplicate order for same patient and medication today.",
                )

            warnings.append(
                {
                    "code": "ORDER_POSSIBLE_DUPLICATE",
                    "message": "This patient already has an order for this medication on a different day.",
                }
            )

    if warnings and not data.confirm:
        logging.warning("Order requires confirmation: warning_codes=%s", [warning["code"] for warning in warnings])
        return WarningResponse(warnings=warnings)

    order = repository.create_order(db, data)

    try:
        generate_care_plan_task.delay(order.id)
    except Exception as exc:
        logging.exception("Care plan Celery dispatch failed for order %s", order.id)
        try:
            repository.mark_order_failed(db, order.id, DISPATCH_FAILURE_MESSAGE)
        except Exception:
            logging.exception("Failed to persist Celery dispatch failure state for order %s", order.id)
        raise OrderDispatchError from exc

    return order

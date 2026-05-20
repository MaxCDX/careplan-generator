from datetime import datetime

from pydantic import BaseModel

from app.patients.schemas import PatientRead
from app.providers.schemas import ProviderRead


class OrderCreate(BaseModel):
    """Request body for creating an Order from the current frontend form."""

    patient_name: str
    mrn: str
    provider_name: str
    provider_npi: str
    diagnosis: str
    medication: str
    clinical_notes: str


class OrderAccepted(BaseModel):
    """Response body for accepted Day 4 queued generation requests."""

    order_id: str
    status: str
    message: str


class OrderRead(BaseModel):
    """Response body for Order APIs with nested patient/provider summaries."""

    id: str
    patient: PatientRead
    provider: ProviderRead
    medication: str
    diagnosis: str
    clinical_notes: str
    status: str
    error_message: str | None = None
    has_care_plan: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

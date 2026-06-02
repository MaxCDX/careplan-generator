from datetime import datetime
import re

from pydantic import BaseModel, field_validator

from app.patients.schemas import PatientRead
from app.providers.schemas import ProviderRead


class OrderCreate(BaseModel):
    """Request body for creating an Order from the frontend intake form."""

    patient_name: str
    patient_dob: str | None = None
    mrn: str
    provider_name: str
    provider_npi: str
    diagnosis: str
    medication: str
    clinical_notes: str
    confirm: bool = False

    @field_validator(
        "patient_name",
        "provider_name",
        "diagnosis",
        "medication",
        "clinical_notes",
    )
    @classmethod
    def required_string_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Required field cannot be empty")
        return cleaned

    @field_validator("provider_npi")
    @classmethod
    def provider_npi_must_be_10_digits(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Provider NPI must be exactly 10 digits")
        return cleaned

    @field_validator("mrn")
    @classmethod
    def mrn_must_be_6_digits(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.fullmatch(r"\d{6}", cleaned):
            raise ValueError("Patient MRN must be exactly 6 digits")
        return cleaned

    @field_validator("patient_dob")
    @classmethod
    def patient_dob_must_be_valid_date(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Patient DOB must use YYYY-MM-DD format") from exc
        return cleaned


class OrderAccepted(BaseModel):
    """Response body for an accepted Celery-backed generation request."""

    order_id: str
    status: str
    message: str


class WarningItem(BaseModel):
    """One business warning that can be confirmed by the user."""

    code: str
    message: str


class WarningResponse(BaseModel):
    """Response body for warning flows that should not create an Order."""

    status: str = "warning"
    requires_confirmation: bool = True
    warnings: list[WarningItem]


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
    care_plan_content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrderStatusRead(BaseModel):
    """Minimal response body for frontend polling."""

    id: str
    status: str
    error_message: str | None = None
    has_care_plan: bool
    care_plan_content: str | None = None

from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.patients.schemas import PatientRead
from app.patients.validators import blank_to_none, parse_birth_date, validate_mrn, validate_name, validate_middle_name
from app.providers.schemas import ProviderRead
from app.providers.validators import validate_npi


class OrderCreate(BaseModel):
    """Request body for creating an Order from the frontend intake form."""

    patient_first_name: str
    patient_middle_name: str | None = None
    patient_last_name: str
    patient_date_of_birth: date | None = None
    mrn: str
    provider_name: str
    provider_npi: str
    diagnosis: str
    medication: str
    clinical_notes: str
    confirm: bool = False

    @field_validator(
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
        return validate_npi(value)

    @field_validator("patient_first_name", "patient_last_name")
    @classmethod
    def check_name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("patient_middle_name")
    @classmethod
    def check_middle_name(cls, value: str | None) -> str | None:
        return validate_middle_name(value)

    @field_validator("mrn")
    @classmethod
    def mrn_must_be_6_digits(cls, value: str) -> str:
        return validate_mrn(value)

    @field_validator("patient_date_of_birth", mode="before")
    @classmethod
    def validate_patient_date_of_birth(cls, value) -> date | None:
        return parse_birth_date(blank_to_none(value))


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


class OrderListResponse(BaseModel):
    """Paginated Order list with a total count before pagination."""

    count: int
    page: int
    page_size: int
    results: list[OrderRead]


class OrderStatusRead(BaseModel):
    """Minimal response body for frontend polling."""

    order_id: str
    status: str
    error_message: str | None = None
    careplan_preview: str | None = None

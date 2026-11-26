from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.patients.validators import validate_diagnosis, validate_mrn, validate_name, validate_middle_name, validate_patient_birth_date


class PatientRead(BaseModel):
    id: str
    first_name: str
    middle_name: str | None
    last_name: str
    mrn: str
    date_of_birth: date | None


class PatientCreate(BaseModel):
    first_name: str
    middle_name: str | None = None
    last_name: str
    mrn: str
    date_of_birth: date | None = None
    sex: Literal["Female", "Male", "Other"] | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    allergies: str | None = None
    primary_diagnosis: str
    additional_diagnoses: list[str] = Field(default_factory=list)

    @field_validator("primary_diagnosis")
    @classmethod
    def check_primary_diagnosis(cls, value: str) -> str:
        return validate_diagnosis(value)

    @field_validator("additional_diagnoses")
    @classmethod
    def check_additional_diagnoses(cls, values: list[str]) -> list[str]:
        return [validate_diagnosis(value) for value in values]

    @field_validator("first_name", "last_name")
    @classmethod
    def check_name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("middle_name")
    @classmethod
    def check_middle_name(cls, value: str | None) -> str | None:
        return validate_middle_name(value)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_date_of_birth(cls, value) -> date | None:
        return validate_patient_birth_date(value)

    @field_validator("mrn")
    @classmethod
    def mrn_must_be_6_digits(cls, value: str) -> str:
        return validate_mrn(value)


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: Literal["Female", "Male", "Other"] | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    allergies: str | None = None
    primary_diagnosis: str | None = None
    additional_diagnoses: list[str] = Field(default_factory=list)
    medication_history: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def check_update_fields(cls, data):
        if isinstance(data, dict):
            if not data:
                raise ValueError("Provide at least one field to update")
            if "mrn" in data:
                raise ValueError("MRN cannot be modified")
        return data

    @field_validator("first_name", "last_name")
    @classmethod
    def check_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Patient name cannot be null")
        return validate_name(value)

    @field_validator("primary_diagnosis")
    @classmethod
    def check_primary_diagnosis(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Primary diagnosis cannot be null")
        return validate_diagnosis(value)

    @field_validator("additional_diagnoses")
    @classmethod
    def check_additional_diagnoses(cls, values: list[str]) -> list[str]:
        return [validate_diagnosis(value) for value in values]

    @field_validator("middle_name")
    @classmethod
    def check_middle_name(cls, value: str | None) -> str | None:
        return validate_middle_name(value)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_date_of_birth(cls, value) -> date | None:
        return validate_patient_birth_date(value)

    @field_validator("medication_history")
    @classmethod
    def check_medications(cls, values: list[str]) -> list[str]:
        medications = [value.strip() for value in values]
        if any(not value for value in medications):
            raise ValueError("Medication entries cannot be blank")
        return medications


class PatientUpdated(BaseModel):
    id: str
    first_name: str
    last_name: str
    mrn: str
    weight_kg: float | None
    allergies: str | None
    updated_at: datetime


class PatientCreated(PatientRead):
    sex: str | None
    weight_kg: float | None
    allergies: str | None
    primary_diagnosis: str
    additional_diagnoses: list[str]
    created_at: datetime


class PatientListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    full_name: str
    mrn: str
    primary_diagnosis: str | None
    created_at: datetime


class PatientListResponse(BaseModel):
    count: int
    page: int
    page_size: int
    results: list[PatientListItem]


class PatientOrderSummary(BaseModel):
    id: str
    medication_name: str
    status: str
    created_at: datetime


class PatientDetail(PatientRead):
    full_name: str
    sex: str | None
    weight_kg: float | None
    allergies: str | None
    primary_diagnosis: str | None
    additional_diagnoses: list[str]
    medication_history: list[str]
    orders: list[PatientOrderSummary]
    created_at: datetime

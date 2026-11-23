from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.patients.validators import parse_birth_date, validate_diagnosis, validate_mrn, validate_name, validate_middle_name


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

    @field_validator("mrn")
    @classmethod
    def mrn_must_be_6_digits(cls, value: str) -> str:
        return validate_mrn(value)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_date_of_birth(cls, value) -> date | None:
        parsed = parse_birth_date(value)
        if parsed is not None and parsed > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return parsed


class PatientCreated(PatientRead):
    sex: str | None
    weight_kg: float | None
    allergies: str | None
    primary_diagnosis: str
    additional_diagnoses: list[str]
    created_at: datetime

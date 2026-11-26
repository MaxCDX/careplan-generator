"""Patient identity rules shared by registration and order intake."""

import re
from datetime import date


def blank_to_none(value):
    return None if isinstance(value, str) and not value.strip() else value


def validate_name(value: str) -> str:
    cleaned = value.strip()
    if not 1 <= len(cleaned) <= 100:
        raise ValueError("Patient name must contain between 1 and 100 characters")
    return cleaned


def validate_middle_name(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return validate_name(value)


def validate_mrn(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"[0-9]{6}", cleaned):
        raise ValueError("Patient MRN must be exactly 6 digits")
    return cleaned


def validate_diagnosis(value: str) -> str:
    code = value.strip().upper()
    if not re.fullmatch(r"[A-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?", code):
        raise ValueError("Invalid ICD-10 code format")
    return code


def parse_birth_date(value) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value.strip()):
        raise ValueError("Date of birth must use YYYY-MM-DD format")
    return date.fromisoformat(value.strip())


def validate_patient_birth_date(value) -> date | None:
    parsed = parse_birth_date(value)
    if parsed is not None and parsed > date.today():
        raise ValueError("Date of birth cannot be in the future")
    return parsed

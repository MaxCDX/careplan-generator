import re


def validate_npi(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"[0-9]{10}", cleaned):
        raise ValueError("Provider NPI must be exactly 10 digits")
    return cleaned

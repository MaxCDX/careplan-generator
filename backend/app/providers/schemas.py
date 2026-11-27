from datetime import datetime

from pydantic import BaseModel, field_validator

from app.providers.validators import validate_npi


class ProviderRead(BaseModel):
    id: str
    name: str
    npi: str


class ProviderCreate(BaseModel):
    name: str
    npi: str
    confirm: bool = False

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not 1 <= len(cleaned) <= 200:
            raise ValueError("Provider name must contain between 1 and 200 characters")
        return cleaned

    @field_validator("npi")
    @classmethod
    def check_npi(cls, value: str) -> str:
        return validate_npi(value)


class ProviderCreated(ProviderRead):
    created_at: datetime

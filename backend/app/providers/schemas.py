from pydantic import BaseModel


class ProviderRead(BaseModel):
    id: str
    name: str
    npi: str

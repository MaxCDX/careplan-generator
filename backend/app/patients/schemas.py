from pydantic import BaseModel


class PatientRead(BaseModel):
    id: str
    name: str
    mrn: str
    dob: str | None = None

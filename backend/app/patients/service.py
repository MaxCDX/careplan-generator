from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError
from app.patients import repository
from app.patients.models import Patient
from app.patients.schemas import PatientCreate


def mrn_conflict(patient: Patient) -> ConflictError:
    return ConflictError(code="PATIENT_MRN_CONFLICT", message="Patient MRN already exists.",
                         detail={"existing_patient_id": patient.id})


def create_patient(db: Session, data: PatientCreate) -> Patient:
    existing = repository.get_patient_by_mrn(db, data.mrn)
    if existing:
        raise mrn_conflict(existing)
    match = repository.get_patient_by_name_and_dob(
        db, first_name=data.first_name, last_name=data.last_name, dob=data.date_of_birth,
    )
    if match:
        raise ConflictError(code="PATIENT_IDENTITY_CONFLICT",
                            message="A patient with the same name and date of birth already exists.",
                            detail={"existing_patient_id": match.id})
    try:
        return repository.insert_patient(db, data)
    except IntegrityError:
        existing = repository.get_patient_by_mrn(db, data.mrn)
        if existing:
            raise mrn_conflict(existing)
        raise

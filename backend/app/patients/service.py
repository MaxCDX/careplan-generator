from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.patients import repository
from app.patients.models import Patient
from app.patients.schemas import PatientCreate, PatientUpdate


def mrn_conflict(patient: Patient) -> ConflictError:
    return ConflictError(code="PATIENT_MRN_CONFLICT", message="Patient MRN already exists.",
                         detail={"existing_patient_id": patient.id})


def identity_conflict(patient: Patient) -> ConflictError:
    return ConflictError(code="PATIENT_IDENTITY_CONFLICT",
                         message="A patient with the same name and date of birth already exists.",
                         detail={"existing_patient_id": patient.id})


def update_patient(db: Session, patient_id: str, data: PatientUpdate) -> Patient:
    patient = repository.get_patient_for_update(db, patient_id)
    if patient is None:
        raise NotFoundError(code="PATIENT_NOT_FOUND", message="Patient not found.")
    changes = data.model_dump(exclude_unset=True)
    identity_fields = {"first_name", "last_name", "date_of_birth"}
    if any(changes[key] != getattr(patient, key) for key in identity_fields.intersection(changes)):
        match = repository.get_patient_by_name_and_dob(
            db, first_name=changes.get("first_name", patient.first_name),
            last_name=changes.get("last_name", patient.last_name),
            dob=changes.get("date_of_birth", patient.date_of_birth), exclude_id=patient.id,
        )
        if match:
            raise identity_conflict(match)
    return repository.save_patient_changes(db, patient, changes)


def create_patient(db: Session, data: PatientCreate) -> Patient:
    existing = repository.get_patient_by_mrn(db, data.mrn)
    if existing:
        raise mrn_conflict(existing)
    match = repository.get_patient_by_name_and_dob(
        db, first_name=data.first_name, last_name=data.last_name, dob=data.date_of_birth,
    )
    if match:
        raise identity_conflict(match)
    try:
        return repository.insert_patient(db, data)
    except IntegrityError:
        existing = repository.get_patient_by_mrn(db, data.mrn)
        if existing:
            raise mrn_conflict(existing)
        raise

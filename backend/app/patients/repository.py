from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.patients.models import Patient
from app.patients.schemas import PatientCreate


def insert_patient(db: Session, data: PatientCreate) -> Patient:
    patient = Patient(**data.model_dump())
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(patient)
    return patient


def get_patient_by_mrn(db: Session, mrn: str) -> Patient | None:
    """Return an existing Patient by MRN."""
    return db.query(Patient).filter(Patient.mrn == mrn).one_or_none()


def get_patient_by_name_and_dob(db: Session, *, first_name: str, last_name: str, dob: date | None) -> Patient | None:
    """Return an existing Patient by identity fields."""
    if not dob:
        return None

    return (
        db.query(Patient)
        .filter(Patient.first_name == first_name, Patient.last_name == last_name, Patient.date_of_birth == dob)
        .order_by(Patient.id)
        .first()
    )


def get_or_create_patient(db: Session, *, first_name: str, middle_name: str | None, last_name: str, mrn: str, dob: date | None = None) -> Patient:
    """Return an existing Patient by MRN or create one for this workflow."""
    patient = get_patient_by_mrn(db, mrn)
    if patient:
        return patient

    patient = Patient(first_name=first_name, middle_name=middle_name, last_name=last_name, mrn=mrn, date_of_birth=dob)
    db.add(patient)
    db.flush()
    return patient

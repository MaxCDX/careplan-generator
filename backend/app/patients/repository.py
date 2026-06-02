from sqlalchemy.orm import Session

from app.patients.models import Patient


def get_patient_by_mrn(db: Session, mrn: str) -> Patient | None:
    """Return an existing Patient by MRN."""
    return db.query(Patient).filter(Patient.mrn == mrn).one_or_none()


def get_patient_by_name_and_dob(db: Session, *, name: str, dob: str | None) -> Patient | None:
    """Return an existing Patient by identity fields."""
    if not dob:
        return None

    return db.query(Patient).filter(Patient.name == name, Patient.dob == dob).one_or_none()


def get_or_create_patient(db: Session, *, name: str, mrn: str, dob: str | None = None) -> Patient:
    """Return an existing Patient by MRN or create one for this workflow."""
    patient = get_patient_by_mrn(db, mrn)
    if patient:
        return patient

    patient = Patient(name=name, mrn=mrn, dob=dob)
    db.add(patient)
    db.flush()
    return patient

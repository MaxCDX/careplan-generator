from sqlalchemy.orm import Session

from app.patients.models import Patient


def get_or_create_patient(db: Session, *, name: str, mrn: str, dob: str | None = None) -> Patient:
    """Return an existing Patient by MRN or create one for this workflow."""
    patient = db.query(Patient).filter(Patient.mrn == mrn).one_or_none()
    if patient:
        return patient

    patient = Patient(name=name, mrn=mrn, dob=dob)
    db.add(patient)
    db.flush()
    return patient

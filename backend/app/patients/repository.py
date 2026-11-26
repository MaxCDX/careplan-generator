from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, load_only
from sqlalchemy.exc import IntegrityError

from app.patients.models import Patient
from app.models import PatientDiagnosis
from app.patients.schemas import PatientCreate


def full_name_contains(search: str):
    """SQL predicate for a literal substring of a patient's display name."""
    escaped = search.replace("/", "//").replace("%", "/%").replace("_", "/_")
    full_name = Patient.first_name + " " + func.coalesce(Patient.middle_name + " ", "") + Patient.last_name
    return full_name.ilike(f"%{escaped}%", escape="/")


def list_patients(db: Session, *, page: int, page_size: int, search: str | None) -> tuple[int, list[Patient]]:
    query = db.query(Patient)
    term = (search or "").strip()
    if term:
        query = query.filter(full_name_contains(term))

    count = query.with_entities(func.count(Patient.id)).scalar()
    offset = (page - 1) * page_size
    if offset >= count:
        return count, []

    patients = (
        query.options(load_only(
            Patient.id, Patient.first_name, Patient.middle_name, Patient.last_name, Patient.mrn,
            Patient.primary_diagnosis, Patient.created_at,
        ))
        .order_by(Patient.last_name, Patient.first_name, Patient.id)
        .limit(page_size)
        .offset(offset)
        .all()
    )
    return count, patients


def insert_patient(db: Session, data: PatientCreate) -> Patient:
    patient = Patient(**data.model_dump(exclude={"additional_diagnoses"}))
    patient.diagnoses = [
        PatientDiagnosis(icd10_code=code, position=position)
        for position, code in enumerate(data.additional_diagnoses)
    ]
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

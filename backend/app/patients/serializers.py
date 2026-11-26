from app.patients.models import Patient
from app.patients.schemas import PatientCreated, PatientListItem, PatientRead


def serialize_patient_list_item(patient: Patient) -> PatientListItem:
    return PatientListItem(
        id=patient.id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        full_name=patient.full_name,
        mrn=patient.mrn,
        primary_diagnosis=patient.primary_diagnosis,
        created_at=patient.created_at,
    )


def serialize_patient(patient: Patient) -> PatientRead:
    return PatientRead(
        id=patient.id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        mrn=patient.mrn,
        date_of_birth=patient.date_of_birth,
    )


def serialize_created_patient(patient: Patient) -> PatientCreated:
    return PatientCreated(
        id=patient.id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        mrn=patient.mrn,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        weight_kg=patient.weight_kg,
        allergies=patient.allergies,
        primary_diagnosis=patient.primary_diagnosis,
        additional_diagnoses=[diagnosis.icd10_code for diagnosis in patient.diagnoses],
        created_at=patient.created_at,
    )

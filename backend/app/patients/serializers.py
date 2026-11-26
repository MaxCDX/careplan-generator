from app.models import Order
from app.patients.models import Patient
from app.patients.schemas import PatientCreated, PatientDetail, PatientListItem, PatientOrderSummary, PatientRead, PatientUpdated


def serialize_updated_patient(patient: Patient) -> PatientUpdated:
    return PatientUpdated(
        id=patient.id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        mrn=patient.mrn,
        weight_kg=patient.weight_kg,
        allergies=patient.allergies,
        updated_at=patient.updated_at,
    )


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


def serialize_patient_detail(patient: Patient, orders: list[Order]) -> PatientDetail:
    return PatientDetail(
        id=patient.id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        full_name=patient.full_name,
        mrn=patient.mrn,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        weight_kg=patient.weight_kg,
        allergies=patient.allergies,
        primary_diagnosis=patient.primary_diagnosis,
        additional_diagnoses=[row.icd10_code for row in patient.diagnoses],
        medication_history=[row.medication_text for row in patient.medication_history],
        orders=[
            PatientOrderSummary(
                id=order.id,
                medication_name=order.medication,
                status=order.status,
                created_at=order.created_at,
            )
            for order in orders
        ],
        created_at=patient.created_at,
    )

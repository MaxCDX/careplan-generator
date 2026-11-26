import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest

from app.models import CarePlan, MedicationHistory, Order, Patient, PatientDiagnosis, Provider
from order_test_support import isolated_client


def make_patient(mrn):
    return Patient(
        first_name="Example", last_name="Patient", mrn=mrn,
        diagnoses=[PatientDiagnosis(icd10_code="I10", position=0)],
        medication_history=[MedicationHistory(medication_text="Example", position=0)],
    )


def test_delete_removes_only_target_patient_and_owned_children():
    with isolated_client() as (client, db):
        patient, other = make_patient("001234"), make_patient("005678")
        db.add_all([patient, other])
        db.commit()
        patient_id, other_id = patient.id, other.id
        response = client.delete(f"/patients/{patient_id}")
        assert response.status_code == 204 and response.content == b""
        db.expunge_all()
        assert db.get(Patient, patient_id) is None
        for model in (PatientDiagnosis, MedicationHistory):
            assert db.query(model).one().patient_id == other_id
        missing = client.delete(f"/patients/{patient_id}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "PATIENT_NOT_FOUND"


@pytest.mark.parametrize("statuses", [
    ["queued"], ["processing"], ["completed"], ["failed"], ["completed", "processing", "queued"],
])
def test_order_conflicts_preserve_patient_and_history(statuses):
    with isolated_client() as (client, db):
        patient = make_patient("001234")
        provider = Provider(name="Example", npi="1234567890")
        orders = [
            Order(patient=patient, provider=provider, medication="Example", diagnosis="I10",
                  clinical_notes="Fictional", status=status)
            for status in statuses
        ]
        for order in orders:
            if order.status == "completed":
                order.care_plan = CarePlan(care_plan_content="Draft", model="mock")
        db.add_all(orders)
        db.commit()
        patient_id = patient.id
        active = sorted(order.id for order in orders if order.status in ("queued", "processing"))
        before = client.get(f"/patients/{patient_id}").json()
        response = client.delete(f"/patients/{patient_id}")
        assert response.status_code == 409
        body = response.json()
        if active:
            assert body["code"] == "PATIENT_HAS_ACTIVE_ORDERS"
            assert body["detail"]["active_orders"] == active
        else:
            assert body["code"] == "PATIENT_HAS_ORDER_HISTORY"
        db.expunge_all()
        assert client.get(f"/patients/{patient_id}").json() == before
        assert db.query(CarePlan).count() == statuses.count("completed")

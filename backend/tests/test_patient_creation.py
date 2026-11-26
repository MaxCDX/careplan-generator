import os
from uuid import UUID

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import MedicationHistory, Patient, Order
from app.orders import service
from order_test_support import isolated_client, order_payload


@pytest.fixture
def registration():
    with isolated_client() as client_and_db:
        yield client_and_db


@pytest.fixture
def dispatched(monkeypatch):
    order_ids = []
    monkeypatch.setattr(service.generate_care_plan_task, "delay", order_ids.append)
    return order_ids


BASE = {"first_name": "John", "last_name": "Smith", "mrn": "001234", "primary_diagnosis": "g70.00"}


def test_medication_history_round_trip_preserves_position(registration):
    client, db = registration
    patient_id = client.post("/patients", json=BASE).json()["id"]
    patient = db.get(Patient, patient_id)
    assert patient.medication_history == []
    patient.medication_history.extend([
        MedicationHistory(position=1, medication_text="Example B 10mg"),
        MedicationHistory(position=0, medication_text="Example A 60mg"),
    ])
    db.commit()
    db.expunge_all()
    rows = db.get(Patient, patient_id).medication_history
    assert [row.medication_text for row in rows] == ["Example A 60mg", "Example B 10mg"]


def test_registration_then_order_and_search(registration, dispatched):
    client, db = registration
    data = dict(BASE, middle_name=" A. ", date_of_birth="1979-06-08", sex="Female",
                weight_kg=72.25, allergies="None known", additional_diagnoses=["i10", "K21.0"])
    response = client.post("/patients", json=data)
    assert response.status_code == 201
    patient = response.json()
    assert UUID(patient["id"]) and patient["created_at"]
    assert patient == {**data, "id": patient["id"], "created_at": patient["created_at"],
                       "middle_name": "A.", "primary_diagnosis": "G70.00",
                       "additional_diagnoses": ["I10", "K21.0"]}
    db.expire_all()
    stored = db.get(Patient, patient["id"])
    assert [(row.position, row.icd10_code) for row in stored.diagnoses] == [(0, "I10"), (1, "K21.0")]
    assert db.query(Order).count() == 0 and dispatched == []
    order = order_payload(patient_first_name="John", patient_last_name="Smith", mrn="001234")
    assert client.post("/orders", json=order).status_code == 202
    result = client.get("/orders", params={"patient_name": "john a. smith"}).json()
    assert result["count"] == 1 and result["results"][0]["patient"]["id"] == patient["id"]


def test_duplicate_policies(registration):
    client, db = registration
    data = dict(BASE, date_of_birth="1979-06-08")
    patient = client.post("/patients", json=data).json()
    for changes, code in [({}, "PATIENT_MRN_CONFLICT"), ({"last_name": "Other"}, "PATIENT_MRN_CONFLICT"),
                          ({"mrn": "009999", "middle_name": "A"}, "PATIENT_IDENTITY_CONFLICT")]:
        response = client.post("/patients", json={**data, **changes})
        assert response.status_code == 409
        assert response.json()["code"] == code
        assert response.json()["detail"] == {"existing_patient_id": patient["id"]}
    assert db.query(Patient).count() == 1
    response = client.post("/patients", json=dict(BASE, mrn="009999", middle_name="  "))
    assert response.status_code == 201
    assert response.json()["middle_name"] is None and response.json()["additional_diagnoses"] == []


def test_order_created_patient_conflicts_with_registration(registration, dispatched):
    client, db = registration
    assert client.post("/orders", json=order_payload(mrn="001234")).status_code == 202
    response = client.post("/patients", json=BASE)
    assert response.status_code == 409
    assert response.json()["detail"]["existing_patient_id"] == db.query(Patient).one().id


@pytest.mark.parametrize("field,value", [
    ("first_name", "  "), ("last_name", ""), ("mrn", 1234), ("mrn", "１２３４５６"),
    ("primary_diagnosis", "G70_00"), ("additional_diagnoses", ["invalid"]),
    ("date_of_birth", "2030-02-30"), ("date_of_birth", "2999-01-01"),
    ("weight_kg", 0), ("weight_kg", -1), ("sex", "invalid"),
])
def test_invalid_patient(registration, field, value):
    client, db = registration
    response = client.post("/patients", json={**BASE, field: value})
    assert response.status_code == 400 and response.json()["code"] == "VALIDATION_ERROR"
    assert db.query(Patient).count() == 0


@pytest.mark.parametrize("missing", BASE)
def test_missing_required_field(registration, missing):
    client, _ = registration
    response = client.post("/patients", json={k: v for k, v in BASE.items() if k != missing})
    assert response.status_code == 400

import os
from datetime import datetime
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import MedicationHistory, Order, Patient, Provider
from app.orders import service
from order_test_support import isolated_client, order_payload


def test_patient_detail_returns_ordered_history_for_this_patient():
    with isolated_client() as (client, db):
        data = {
            "mrn": "001234", "first_name": "John", "middle_name": "A.", "last_name": "Smith",
            "date_of_birth": "1979-06-08", "sex": "Male", "weight_kg": 72,
            "allergies": "None known", "primary_diagnosis": "G70.00",
            "additional_diagnoses": ["K21.0", "I10"],
        }
        created = client.post("/patients", json=data).json()
        patient_id = created["id"]
        other = Patient(first_name="Jane", last_name="Smith", mrn="002345")
        provider = Provider(name="Fictional Provider", npi="1234567890")
        db.add_all([other, provider])
        db.flush()
        for position, name in [(1, "Example B"), (0, "Example A")]:
            db.add(MedicationHistory(patient_id=patient_id, position=position, medication_text=name))
        order_ids = sorted(str(uuid4()) for _ in range(3))
        for i, order_id in enumerate(order_ids):
            db.add(Order(
                id=order_id, patient_id=patient_id if i < 2 else other.id, provider_id=provider.id,
                medication="IVIG", status="completed", diagnosis="G70.00", clinical_notes="Fictional",
                created_at=datetime(2025, 10, 16),
            ))
        db.commit()
        db.expunge_all()
        response = client.get(f"/patients/{patient_id}")
        assert response.status_code == 200
        assert response.json() == {
            **created, "full_name": "John A. Smith", "medication_history": ["Example A", "Example B"],
            "orders": [
                {"id": order_id, "medication_name": "IVIG", "status": "completed",
                 "created_at": "2025-10-16T00:00:00"}
                for order_id in reversed(order_ids[:2])
            ],
        }
        history = client.get(f"/patients/{patient_id}/orders")
        assert history.status_code == 200
        assert history.json() == {
            "patient_id": patient_id, "patient_name": "John A. Smith", "orders": response.json()["orders"],
        }


def test_order_intake_patient_detail(monkeypatch):
    monkeypatch.setattr(service.generate_care_plan_task, "delay", lambda order_id: None)
    with isolated_client() as (client, db):
        order = client.post("/orders", json=order_payload()).json()
        patient = db.query(Patient).one()
        response = client.get(f"/patients/{patient.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["primary_diagnosis"] is None
        assert body["additional_diagnoses"] == body["medication_history"] == []
        assert [row["id"] for row in body["orders"]] == [order["order_id"]]


def test_registered_patient_without_orders_and_missing_patient():
    with isolated_client() as (client, db):
        patient = Patient(first_name="John", last_name="Doe", mrn="001234")
        db.add(patient)
        db.commit()
        assert client.get(f"/patients/{patient.id}").json()["orders"] == []
        history = client.get(f"/patients/{patient.id}/orders")
        assert history.status_code == 200
        assert history.json() == {"patient_id": patient.id, "patient_name": "John Doe", "orders": []}
        missing_history = client.get(f"/patients/{uuid4()}/orders")
        assert missing_history.status_code == 404
        assert missing_history.json()["code"] == "PATIENT_NOT_FOUND"
        missing = client.get(f"/patients/{uuid4()}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "PATIENT_NOT_FOUND"

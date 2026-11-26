import os
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import Patient
from order_test_support import isolated_client


@pytest.fixture
def profile():
    with isolated_client() as (client, db):
        data = dict(first_name="John", last_name="Smith", mrn="001234",
                    primary_diagnosis="G70.00", date_of_birth="1980-01-02",
                    additional_diagnoses=["I10"], allergies="Example")
        patient = client.post("/patients", json=data).json()
        yield client, db, f"/patients/{patient['id']}"


def test_partial_update_and_clear(profile):
    client, _, url = profile
    response = client.put(url, json={"weight_kg": 75})
    assert response.status_code == 200
    assert response.json()["weight_kg"] == 75 and response.json()["mrn"] == "001234"
    assert response.json()["updated_at"]
    assert client.get(url).json()["allergies"] == "Example"
    assert client.put(url, json={"allergies": None}).status_code == 200
    assert client.get(url).json()["allergies"] is None


def test_child_only_update_replaces_in_order_and_updates_timestamp(profile):
    client, db, url = profile
    db.query(Patient).update({Patient.updated_at: datetime(2000, 1, 1)})
    db.commit()
    for meds in (["A", "B"], ["B", "C"], []):
        response = client.put(url, json={"medication_history": meds, "additional_diagnoses": ["k21.0", "I10"]})
        assert response.status_code == 200
        assert datetime.fromisoformat(response.json()["updated_at"]).year > 2000
        detail = client.get(url).json()
        assert detail["medication_history"] == meds and detail["additional_diagnoses"] == ["K21.0", "I10"]
    assert client.put(url, json={"additional_diagnoses": []}).status_code == 200
    assert client.get(url).json()["additional_diagnoses"] == []


@pytest.mark.parametrize("invalid", [
    {}, {"mrn": "001234"}, {"unknown": 1}, {"first_name": None}, {"last_name": " "},
    {"weight_kg": 0}, {"sex": "invalid"}, {"date_of_birth": "2999-01-01"},
    {"primary_diagnosis": None}, {"additional_diagnoses": ["bad!"]},
    {"medication_history": [" "]}, {"medication_history": None},
])
def test_validation_no_partial_write(profile, invalid):
    client, _, url = profile
    before = client.get(url).json()
    payload = {**invalid, "allergies": "changed"} if invalid else {}
    response = client.put(url, json=payload)
    assert response.status_code == 400 and response.json()["code"] == "VALIDATION_ERROR"
    assert client.get(url).json() == before


def test_identity_change_excludes_self_and_checks_final_identity(profile):
    client, _, url = profile
    assert client.put(url, json={"first_name": "John"}).status_code == 200
    other = client.post("/patients", json=dict(first_name="Jane", last_name="Smith", mrn="000999",
                        date_of_birth="1980-01-02", primary_diagnosis="I10")).json()
    response = client.put(url, json={"first_name": "Jane", "additional_diagnoses": []})
    assert response.status_code == 409
    assert response.json()["detail"]["existing_patient_id"] == other["id"]
    assert client.get(url).json()["additional_diagnoses"] == ["I10"]


def test_database_failure_restores_parent_and_both_collections(profile):
    client, db, url = profile
    # Fail the replacement INSERT after old positions have been flushed.
    assert client.put(url, json={"medication_history": ["Original"]}).status_code == 200
    db.query(Patient).update({Patient.updated_at: datetime(2000, 1, 1)})
    db.execute(text("""
        CREATE TRIGGER reject_medication BEFORE INSERT ON medication_history
        BEGIN SELECT RAISE(ABORT, 'test insert failure'); END
    """))
    db.commit()
    before = client.get(url).json()
    with pytest.raises(IntegrityError, match="test insert failure"):
        client.put(url, json={"medication_history": ["Replacement"], "additional_diagnoses": ["K21.0"],
                              "allergies": "changed"})
    db.expunge_all()
    assert client.get(url).json() == before
    assert db.query(Patient).one().updated_at == datetime(2000, 1, 1)


def test_missing_patient_and_update_of_basic_record(profile):
    client, db, _ = profile
    assert client.put(f"/patients/{uuid4()}", json={"weight_kg": 75}).status_code == 404
    basic = Patient(first_name="A", last_name="B", mrn="000111")
    db.add(basic)
    db.commit()
    assert client.put(f"/patients/{basic.id}", json={"weight_kg": 75}).status_code == 200

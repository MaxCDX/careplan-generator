import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Order
from app.orders import service


def order_payload(**overrides):
    payload = {
        "patient_name": "Test Patient",
        "patient_dob": "1979-06-08",
        "mrn": "123456",
        "provider_name": "Dr. Test",
        "provider_npi": "1234567890",
        "diagnosis": "G70.00",
        "medication": "IVIG",
        "clinical_notes": "Fictional clinical note.",
    }
    payload.update(overrides)
    return payload


class FakeGenerateCarePlanTask:
    dispatched_order_ids = []

    @classmethod
    def delay(cls, order_id):
        cls.dispatched_order_ids.append(order_id)


def make_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    FakeGenerateCarePlanTask.dispatched_order_ids = []
    monkeypatch.setattr(service, "generate_care_plan_task", FakeGenerateCarePlanTask)
    app.dependency_overrides[get_db] = lambda: db

    return TestClient(app), db


def close_client(db):
    app.dependency_overrides.clear()
    db.close()


def assert_invalid_request_does_not_create_order_or_dispatch(response, db):
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["message"] == "Invalid request input."
    assert isinstance(response.json()["detail"], list)
    assert db.query(Order).count() == 0
    assert FakeGenerateCarePlanTask.dispatched_order_ids == []


def test_invalid_provider_npi_letters_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(provider_npi="abc"))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)


def test_invalid_provider_npi_too_short_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(provider_npi="123"))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)


def test_invalid_patient_mrn_letters_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(mrn="abc"))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)


def test_invalid_patient_mrn_too_short_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(mrn="123"))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)


def test_whitespace_required_string_field_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(patient_name="   "))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)


def test_invalid_patient_dob_returns_400_without_order_or_dispatch(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload(patient_dob="not-a-date"))

        assert_invalid_request_does_not_create_order_or_dispatch(response, db)
    finally:
        close_client(db)

import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Order, Patient, Provider
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


def create_patient(db, *, name="Test Patient", mrn="123456", dob="1979-06-08"):
    patient = Patient(name=name, mrn=mrn, dob=dob)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def create_provider(db, *, name="Dr. Test", npi="1234567890"):
    provider = Provider(name=name, npi=npi)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def create_order(db, *, patient, provider, medication="IVIG", created_at=None):
    order = Order(
        patient_id=patient.id,
        provider_id=provider.id,
        medication=medication,
        diagnosis="G70.00",
        clinical_notes="Existing fictional note.",
        status="completed",
        created_at=created_at or datetime.now(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def test_valid_clean_request_creates_order_and_dispatches_celery(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        response = client.post("/orders", json=order_payload())

        assert response.status_code == 202
        assert response.json()["status"] == "queued"
        assert response.json()["message"] == "Care plan generation request accepted"
        assert db.query(Order).count() == 1
        assert len(FakeGenerateCarePlanTask.dispatched_order_ids) == 1
    finally:
        close_client(db)


def test_provider_same_npi_same_name_reuses_provider(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        provider = create_provider(db)

        response = client.post("/orders", json=order_payload())

        assert response.status_code == 202
        assert db.query(Provider).count() == 1
        order = db.query(Order).one()
        assert order.provider_id == provider.id
        assert len(FakeGenerateCarePlanTask.dispatched_order_ids) == 1
    finally:
        close_client(db)


def test_provider_same_npi_different_name_blocks_with_409(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        create_provider(db, name="Dr. Existing")

        response = client.post("/orders", json=order_payload(provider_name="Dr. Different"))

        assert response.status_code == 409
        assert response.json() == {
            "status": "error",
            "code": "PROVIDER_NPI_CONFLICT",
            "message": "Provider NPI already belongs to a different provider name.",
            "detail": {},
        }
        assert db.query(Order).count() == 0
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_patient_same_mrn_same_identity_reuses_patient(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        patient = create_patient(db)

        response = client.post("/orders", json=order_payload())

        assert response.status_code == 202
        assert db.query(Patient).count() == 1
        order = db.query(Order).one()
        assert order.patient_id == patient.id
        assert len(FakeGenerateCarePlanTask.dispatched_order_ids) == 1
    finally:
        close_client(db)


def test_patient_same_mrn_mismatched_identity_warns_without_order(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        create_patient(db, name="Existing Patient")

        response = client.post("/orders", json=order_payload(patient_name="Different Patient"))

        assert response.status_code == 200
        assert response.json()["status"] == "warning"
        assert response.json()["requires_confirmation"] is True
        assert response.json()["warnings"][0]["code"] == "PATIENT_MRN_MISMATCH"
        assert db.query(Order).count() == 0
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_patient_same_identity_different_mrn_warns_without_order(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        create_patient(db, mrn="999999")

        response = client.post("/orders", json=order_payload(mrn="123456"))

        assert response.status_code == 200
        assert response.json()["status"] == "warning"
        assert response.json()["warnings"][0]["code"] == "PATIENT_POSSIBLE_DUPLICATE"
        assert db.query(Order).count() == 0
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_same_patient_same_medication_same_day_blocks_with_409(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        patient = create_patient(db)
        provider = create_provider(db)
        create_order(db, patient=patient, provider=provider)

        response = client.post("/orders", json=order_payload())

        assert response.status_code == 409
        assert response.json() == {
            "status": "error",
            "code": "DUPLICATE_ORDER_SAME_DAY",
            "message": "Duplicate order for same patient and medication today.",
            "detail": {},
        }
        assert db.query(Order).count() == 1
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_same_patient_same_medication_different_day_warns_when_confirm_false(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        patient = create_patient(db)
        provider = create_provider(db)
        create_order(
            db,
            patient=patient,
            provider=provider,
            created_at=datetime.now() - timedelta(days=5),
        )

        response = client.post("/orders", json=order_payload())

        assert response.status_code == 200
        assert response.json()["status"] == "warning"
        assert response.json()["warnings"][0]["code"] == "ORDER_POSSIBLE_DUPLICATE"
        assert db.query(Order).count() == 1
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_same_patient_same_medication_different_day_proceeds_when_confirm_true(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        patient = create_patient(db)
        provider = create_provider(db)
        create_order(
            db,
            patient=patient,
            provider=provider,
            created_at=datetime.now() - timedelta(days=5),
        )

        response = client.post("/orders", json=order_payload(confirm=True))

        assert response.status_code == 202
        assert db.query(Order).count() == 2
        assert len(FakeGenerateCarePlanTask.dispatched_order_ids) == 1
    finally:
        close_client(db)


def test_warning_does_not_dispatch_celery(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        create_patient(db, name="Existing Patient")

        response = client.post("/orders", json=order_payload(patient_name="Different Patient"))

        assert response.status_code == 200
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)


def test_blocking_error_does_not_dispatch_celery(monkeypatch):
    client, db = make_client(monkeypatch)
    try:
        create_provider(db, name="Dr. Existing")

        response = client.post("/orders", json=order_payload(provider_name="Dr. Different"))

        assert response.status_code == 409
        assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    finally:
        close_client(db)

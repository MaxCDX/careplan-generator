import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.orders import repository


def make_order(status="queued"):
    patient = SimpleNamespace(id="patient-1", name="Test Patient", mrn="123456", dob=None)
    provider = SimpleNamespace(id="provider-1", name="Dr. Test", npi="1234567890")
    return SimpleNamespace(
        id="order-1",
        patient=patient,
        provider=provider,
        medication="IVIG",
        diagnosis="G70.00",
        clinical_notes="Fictional clinical note.",
        status=status,
        error_message=None,
        care_plan=None,
        created_at=None,
        updated_at=None,
    )


def order_payload():
    return {
        "patient_name": "Test Patient",
        "mrn": "123456",
        "provider_name": "Dr. Test",
        "provider_npi": "1234567890",
        "diagnosis": "G70.00",
        "medication": "IVIG",
        "clinical_notes": "Fictional clinical note.",
    }


def test_create_order_dispatches_celery_task_and_returns_accepted(monkeypatch):
    dispatched_order_ids = []

    def fake_create_order(db, data):
        return make_order()

    class FakeGenerateCarePlanTask:
        @staticmethod
        def delay(order_id):
            dispatched_order_ids.append(order_id)

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(repository, "create_order", fake_create_order)
    monkeypatch.setattr("app.orders.routes.generate_care_plan_task", FakeGenerateCarePlanTask)

    try:
        response = TestClient(app).post("/orders", json=order_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {
        "order_id": "order-1",
        "status": "queued",
        "message": "Care plan generation request accepted",
    }
    assert dispatched_order_ids == ["order-1"]


def test_create_order_marks_order_failed_when_celery_dispatch_fails(monkeypatch):
    order = make_order()
    failed_orders = []

    def fake_create_order(db, data):
        return order

    def fake_mark_failed(db, order_id, error_message):
        failed_orders.append((order_id, error_message))

    class FakeGenerateCarePlanTask:
        @staticmethod
        def delay(order_id):
            raise RuntimeError("celery unavailable")

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(repository, "create_order", fake_create_order)
    monkeypatch.setattr(repository, "mark_order_failed", fake_mark_failed)
    monkeypatch.setattr("app.orders.routes.generate_care_plan_task", FakeGenerateCarePlanTask)

    try:
        response = TestClient(app).post("/orders", json=order_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Care plan request could not be queued. Please try again later."
    assert failed_orders == [("order-1", "Failed to enqueue care plan generation request.")]

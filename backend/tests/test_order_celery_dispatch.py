import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
import pytest

from app.database import get_db
from app.main import app
from app.orders import repository
from app.orders import service


def make_order(status="queued"):
    patient = SimpleNamespace(id="patient-1", first_name="Test", middle_name=None, last_name="Patient", full_name="Test Patient", mrn="123456", date_of_birth=None)
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


def make_completed_order_with_care_plan():
    order = make_order(status="completed")
    order.care_plan = SimpleNamespace(
        id="care-plan-1",
        care_plan_content="Generated care plan content",
        model="test-model",
        created_at=None,
    )
    return order


def order_payload():
    return {
        "patient_first_name": "Test",
        "patient_last_name": "Patient",
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
    monkeypatch.setattr(service.provider_repository, "get_provider_by_npi", lambda db, npi: None)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_mrn", lambda db, mrn: None)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_name_and_dob", lambda db, **kwargs: None)
    monkeypatch.setattr(repository, "create_order", fake_create_order)
    monkeypatch.setattr(service, "generate_care_plan_task", FakeGenerateCarePlanTask)

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
    monkeypatch.setattr(service.provider_repository, "get_provider_by_npi", lambda db, npi: None)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_mrn", lambda db, mrn: None)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_name_and_dob", lambda db, **kwargs: None)
    monkeypatch.setattr(repository, "create_order", fake_create_order)
    monkeypatch.setattr(repository, "mark_order_failed", fake_mark_failed)
    monkeypatch.setattr(service, "generate_care_plan_task", FakeGenerateCarePlanTask)

    try:
        response = TestClient(app).post("/orders", json=order_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "code": "CARE_PLAN_QUEUE_UNAVAILABLE",
        "message": "Care plan request could not be queued. Please try again later.",
        "detail": {},
    }
    assert failed_orders == [("order-1", "Failed to enqueue care plan generation request.")]


def test_get_order_returns_status_error_and_care_plan_content(monkeypatch):
    def fake_get_order(db, order_id):
        assert order_id == "order-1"
        order = make_completed_order_with_care_plan()
        order.error_message = None
        return order

    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(repository, "get_order", fake_get_order)

    try:
        response = TestClient(app).get("/orders/order-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "order-1"
    assert response.json()["status"] == "completed"
    assert response.json()["error_message"] is None
    assert response.json()["care_plan_content"] == "Generated care plan content"


def test_get_order_returns_404_for_missing_order(monkeypatch):
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(repository, "get_order", lambda db, order_id: None)

    try:
        response = TestClient(app).get("/orders/missing-order")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "code": "ORDER_NOT_FOUND",
        "message": "Order not found.",
        "detail": {},
    }


@pytest.mark.parametrize("state,content,extra", [
    ("queued", None, {}),
    ("processing", None, {}),
    ("failed", None, {"error_message": "Generation failed."}),
    ("completed", "x" * 200, {"careplan_preview": "x" * 200}),
    ("completed", "文" * 240, {"careplan_preview": "文" * 200 + "…"}),
])
def test_get_order_status_returns_minimal_polling_payload(monkeypatch, state, content, extra):
    from app.models import CarePlan, Order
    from order_test_support import isolated_client

    monkeypatch.setattr(service.generate_care_plan_task, "delay", lambda order_id: None)
    with isolated_client() as (client, db):
        order_id = client.post("/orders", json=order_payload()).json()["order_id"]
        order = db.get(Order, order_id)
        order.status = state
        order.error_message = "Generation failed."
        if content:
            order.care_plan = CarePlan(care_plan_content=content, model="mock")
        db.commit()
        response = client.get(f"/orders/{order_id}/status")
        assert response.status_code == 200
        assert response.json() == {"order_id": order_id, "status": state, **extra}
        if content:
            assert client.get(f"/orders/{order_id}").json()["care_plan_content"] == content


def test_get_order_status_returns_404_for_missing_order(monkeypatch):
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(repository, "get_status_snapshot", lambda db, order_id: None)

    try:
        response = TestClient(app).get("/orders/missing-order/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "code": "ORDER_NOT_FOUND",
        "message": "Order not found.",
        "detail": {},
    }


def test_create_order_openapi_documents_warning_and_error_responses():
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    post_responses = response.json()["paths"]["/orders"]["post"]["responses"]

    assert "200" in post_responses
    assert post_responses["200"]["description"] == "Business warning requiring confirmation"
    assert "400" in post_responses
    assert post_responses["400"]["description"] == "Invalid request input"
    assert "409" in post_responses
    assert post_responses["409"]["description"] == "Business conflict"
    assert "503" in post_responses
    assert post_responses["503"]["description"] == "Queue unavailable"

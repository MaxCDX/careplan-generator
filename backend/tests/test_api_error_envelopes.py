import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from app.care_plans import routes as care_plan_routes
from app.database import get_db
from app.external_orders import routes as external_order_routes
from app.llm.errors import LLMConfigurationError
from app.main import app


def request_with_db(method: str, path: str, db, **kwargs):
    app.dependency_overrides[get_db] = lambda: db
    try:
        return TestClient(app).request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


def test_external_order_normalization_failure_uses_app_error_envelope(monkeypatch):
    def fail_normalization(source, payload):
        raise ValueError("unsupported payload")

    monkeypatch.setattr(
        external_order_routes,
        "normalize_external_order",
        fail_normalization,
    )

    response = request_with_db("POST", "/external-orders/clinic_b", object(), json={})

    assert response.status_code == 400
    assert response.json() == {
        "status": "error",
        "code": "INVALID_EXTERNAL_ORDER",
        "message": "Invalid external order input.",
        "detail": {"error": "unsupported payload"},
    }


def test_generate_care_plan_missing_order_uses_app_error_envelope(monkeypatch):
    monkeypatch.setattr(
        care_plan_routes.order_repository,
        "get_order",
        lambda db, order_id: None,
    )

    response = request_with_db(
        "POST",
        "/care-plans",
        object(),
        json={"order_id": "missing-order"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "code": "ORDER_NOT_FOUND",
        "message": "Order not found.",
        "detail": {},
    }


def test_generate_care_plan_existing_plan_uses_app_error_envelope(monkeypatch):
    order = SimpleNamespace(care_plan=object())
    monkeypatch.setattr(
        care_plan_routes.order_repository,
        "get_order",
        lambda db, order_id: order,
    )

    response = request_with_db(
        "POST",
        "/care-plans",
        object(),
        json={"order_id": "order-1"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "status": "error",
        "code": "CARE_PLAN_ALREADY_EXISTS",
        "message": "Care plan already exists for this order.",
        "detail": {},
    }


def test_generate_care_plan_llm_error_uses_safe_app_error_envelope(monkeypatch):
    class FakeDB:
        def add(self, instance):
            pass

        def commit(self):
            pass

        def refresh(self, instance):
            pass

        def rollback(self):
            pass

    order = SimpleNamespace(
        id="order-1",
        care_plan=None,
        status="queued",
        error_message=None,
    )
    monkeypatch.setattr(
        care_plan_routes.order_repository,
        "get_order",
        lambda db, order_id: order,
    )

    def fail_generation(order, model):
        raise LLMConfigurationError("provider-secret-detail")

    monkeypatch.setattr(
        care_plan_routes,
        "generate_care_plan_content",
        fail_generation,
    )

    response = request_with_db(
        "POST",
        "/care-plans",
        FakeDB(),
        json={"order_id": "order-1"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "code": "CARE_PLAN_GENERATION_UNAVAILABLE",
        "message": "Care plan generation is currently unavailable. Please try again later.",
        "detail": {},
    }
    assert "provider-secret-detail" not in response.text
    assert order.status == "failed"
    assert order.error_message == "Care plan generation failed. Please try again later."


def test_generate_care_plan_unexpected_error_is_not_converted_to_503(monkeypatch):
    class FakeDB:
        def add(self, instance):
            pass

        def commit(self):
            pass

        def refresh(self, instance):
            pass

        def rollback(self):
            pass

    order = SimpleNamespace(
        id="order-1",
        care_plan=None,
        status="queued",
        error_message=None,
    )
    monkeypatch.setattr(
        care_plan_routes.order_repository,
        "get_order",
        lambda db, order_id: order,
    )

    def fail_generation(order, model):
        raise RuntimeError("unexpected-code-error")

    monkeypatch.setattr(
        care_plan_routes,
        "generate_care_plan_content",
        fail_generation,
    )

    with pytest.raises(RuntimeError, match="unexpected-code-error"):
        request_with_db(
            "POST",
            "/care-plans",
            FakeDB(),
            json={"order_id": "order-1"},
        )

    assert order.status == "failed"
    assert order.error_message == "Care plan generation failed. Please try again later."


def test_get_care_plan_missing_plan_uses_app_error_envelope(monkeypatch):
    monkeypatch.setattr(
        care_plan_routes.care_plan_repository,
        "get_care_plan",
        lambda db, care_plan_id: None,
    )

    response = request_with_db("GET", "/care-plans/missing-plan", object())

    assert response.status_code == 404
    assert response.json() == {
        "status": "error",
        "code": "CARE_PLAN_NOT_FOUND",
        "message": "Care plan not found.",
        "detail": {},
    }

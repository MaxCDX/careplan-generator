import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.care_plans import routes as care_plan_routes
from app.database import get_db
from app.external_orders import routes as external_order_routes
from app.external_orders.errors import ExternalOrderInputError
from app.main import app


def request_with_db(method: str, path: str, db, **kwargs):
    app.dependency_overrides[get_db] = lambda: db
    try:
        return TestClient(app).request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


def test_external_order_normalization_failure_uses_app_error_envelope(monkeypatch):
    def fail_normalization(source, payload):
        raise ExternalOrderInputError("unsupported payload")

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
        "detail": {},
    }


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


def test_care_plan_openapi_is_read_only():
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    care_plan_routes = response.json()["paths"]["/care-plans"]
    assert "get" in care_plan_routes
    assert "post" not in care_plan_routes

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.orders import repository as order_repository


def get_metrics(client: TestClient) -> str:
    response = client.get("/metrics")
    assert response.status_code == 200
    return response.text


def test_metrics_endpoint_returns_prometheus_text_format():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "python_gc_objects_collected_total" in response.text
    assert "python_info" in response.text


def test_normal_api_request_increments_http_metrics(monkeypatch):
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(order_repository, "get_order", lambda db, order_id: None)

    try:
        with TestClient(app) as client:
            client.get("/orders/missing-order/status")
            metrics = get_metrics(client)
    finally:
        app.dependency_overrides.clear()

    assert "http_requests_total" in metrics
    assert 'handler="/orders/{order_id}/status"' in metrics
    assert 'method="GET"' in metrics
    assert 'status="404"' in metrics


def test_dynamic_paths_use_route_templates_instead_of_raw_order_ids(monkeypatch):
    raw_order_id = "raw-order-id-must-not-be-a-metric-label"
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(order_repository, "get_order", lambda db, order_id: None)

    try:
        with TestClient(app) as client:
            client.get(f"/orders/{raw_order_id}/status")
            metrics = get_metrics(client)
    finally:
        app.dependency_overrides.clear()

    assert raw_order_id not in metrics
    assert 'handler="/orders/{order_id}/status"' in metrics


def test_metrics_endpoint_is_excluded_from_request_metrics():
    with TestClient(app) as client:
        get_metrics(client)
        metrics = get_metrics(client)

    assert 'handler="/metrics"' not in metrics

import os
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import Order, Patient, Provider
from app.orders import service
from app.tasks import care_plan_tasks
from order_test_support import isolated_client


@pytest.fixture
def workflow():
    with isolated_client() as (client, db):
        order = Order(patient=Patient(first_name="Test", last_name="Patient", mrn="001234"),
                      provider=Provider(name="Provider", npi="1234567890"), medication="Example",
                      diagnosis="I10", clinical_notes="Fictional", status="failed", error_message="Old error")
        db.add(order)
        db.commit()
        yield client, db, order


def test_failed_order_restarts_once_and_worker_completes(workflow, monkeypatch):
    client, db, order = workflow
    dispatched = []
    monkeypatch.setattr(service.retry_care_plan_task, "delay", dispatched.append)
    url = f"/orders/{order.id}/retry"
    response = client.post(url)
    assert response.status_code == 202
    assert response.json() == {"order_id": order.id, "status": "processing", "message": "CarePlan generation restarted"}
    db.refresh(order)
    assert order.status == "processing" and order.error_message is None
    assert client.post(url).status_code == 409
    assert dispatched == [order.id]
    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: type(db)(bind=db.get_bind()))
    monkeypatch.setattr(care_plan_tasks, "generate_care_plan_content", lambda order, model: "New plan")
    service.retry_care_plan_task.run(order.id)
    db.refresh(order)
    assert order.status == "completed" and order.care_plan.care_plan_content == "New plan"


@pytest.mark.parametrize("state", ["queued", "processing", "completed"])
def test_nonfailed_orders_cannot_retry(workflow, monkeypatch, state):
    client, db, order = workflow
    monkeypatch.setattr(service.retry_care_plan_task, "delay", lambda *_: pytest.fail("unexpected dispatch"))
    order.status = state
    db.commit()
    response = client.post(f"/orders/{order.id}/retry")
    assert response.status_code == 409
    assert response.json() == {"error": "Order is not in failed status", "current_status": state}
    assert client.post(f"/orders/{uuid4()}/retry").status_code == 404


def test_dispatch_failure_leaves_order_retryable(workflow, monkeypatch):
    client, db, order = workflow
    def unavailable(order_id):
        raise RuntimeError("broker unavailable")
    monkeypatch.setattr(service.retry_care_plan_task, "delay", unavailable)
    assert client.post(f"/orders/{order.id}/retry").status_code == 503
    db.refresh(order)
    assert order.status == "failed" and order.error_message == service.DISPATCH_FAILURE_MESSAGE

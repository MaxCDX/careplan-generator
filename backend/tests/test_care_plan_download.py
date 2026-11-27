import os
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import CarePlan, Order, Patient, Provider
from order_test_support import isolated_client


@pytest.mark.parametrize("state,has_plan", [
    ("completed", True), ("completed", False), ("processing", True),
    ("queued", True), ("failed", True), (None, False),
])
def test_download_requires_completed_order_with_saved_plan(state, has_plan):
    with isolated_client() as (client, db):
        order_id = str(uuid4())
        content = "第一节\n" + "Fictional plan. " * 25 + "\n"
        if state:
            order = Order(
                id=order_id, status=state, medication="Example", diagnosis="I10", clinical_notes="Fictional",
                patient=Patient(first_name="Example", last_name="Patient", mrn="001234"),
                provider=Provider(name="Example Provider", npi="1234567890"),
            )
            if has_plan:
                order.care_plan = CarePlan(care_plan_content=content, model="mock")
            db.add(order)
            db.commit()

        response = client.get(f"/orders/{order_id}/careplan/download")
        if state == "completed" and has_plan:
            assert response.status_code == 200
            assert response.headers["content-type"].split(";")[0] == "text/plain"
            assert response.headers["content-disposition"] == f'attachment; filename="careplan_order_{order_id}.txt"'
            assert response.content == content.encode("utf-8")
        else:
            assert response.status_code == 404
            assert response.json() == {"error": "CarePlan not yet generated"}

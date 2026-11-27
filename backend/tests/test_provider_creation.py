import os
from datetime import datetime
from uuid import UUID

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import Order, Provider
from app.orders import service as order_service
from order_test_support import isolated_client, order_payload


BASE = {"name": "Dr. Jane Wilson", "npi": "0012345678"}


def test_same_name_can_be_confirmed_but_npi_cannot():
    with isolated_client() as (client, db):
        first = client.post("/providers", json=BASE)
        assert first.status_code == 201
        original = first.json()
        assert UUID(original["id"]) and datetime.fromisoformat(original["created_at"])
        assert original["npi"] == BASE["npi"]
        second = {"name": "  DR. JANE WILSON  ", "npi": "0023456789"}
        warning = client.post("/providers", json=second)
        assert warning.status_code == 409
        assert warning.json()["code"] == "PROVIDER_POSSIBLE_DUPLICATE"
        assert warning.json()["detail"] == {"existing_provider_id": original["id"], "existing_npi": BASE["npi"]}
        assert db.query(Provider).count() == 1
        confirmed = client.post("/providers", json={**second, "confirm": True})
        assert confirmed.status_code == 201
        assert confirmed.json()["name"] == second["name"].strip()
        for name, confirm in [(BASE["name"], False), (BASE["name"], True), ("Different", True)]:
            blocked = client.post("/providers", json={**BASE, "name": name, "confirm": confirm})
            assert blocked.status_code == 409
            assert blocked.json()["code"] == "PROVIDER_NPI_CONFLICT"
            assert blocked.json()["detail"]["existing_provider_id"] == original["id"]
        assert db.query(Provider).count() == 2


def test_distinct_names_and_order_reuse(monkeypatch):
    with isolated_client() as (client, db):
        provider = client.post("/providers", json=BASE).json()
        assert client.post("/providers", json={"name": "Dr. Jane Li", "npi": "1234567890"}).status_code == 201
        monkeypatch.setattr(order_service.generate_care_plan_task, "delay", lambda order_id: None)
        response = client.post("/orders", json=order_payload(provider_name=BASE["name"], provider_npi=BASE["npi"]))
        assert response.status_code == 202
        assert db.query(Order).one().provider_id == provider["id"]
        assert db.query(Provider).count() == 2


@pytest.mark.parametrize("invalid", [
    {"name": " "}, {"name": "x" * 201}, {"npi": "123"}, {"npi": "012345678x"}, {"npi": 1234567890},
])
def test_invalid_payload_with_confirmation(invalid):
    with isolated_client() as (client, db):
        response = client.post("/providers", json={**BASE, **invalid, "confirm": True})
        assert response.status_code == 400 and response.json()["code"] == "VALIDATION_ERROR"
        assert db.query(Provider).count() == 0

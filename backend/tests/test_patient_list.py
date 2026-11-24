import os
from uuid import UUID

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.models import Patient
from order_test_support import isolated_client


@pytest.fixture
def client():
    with isolated_client() as (client, db):
        # Insert ties in reverse UUID order so ordering by name alone is insufficient.
        for i in reversed(range(23)):
            db.add(Patient(
                id=str(UUID(int=i + 1)), mrn=f"{i:06d}",
                first_name="Zoe" if i == 0 else "John",
                middle_name="A." if i == 2 else None,
                last_name="Adams" if i < 2 else "Smith",
            ))
        db.commit()
        yield client


def test_default_page_and_public_fields(client):
    response = client.get("/patients")
    assert response.status_code == 200
    body = response.json()
    assert (body["count"], body["page"], body["page_size"]) == (23, 1, 20)
    assert len(body["results"]) == 20
    first = body["results"][0]
    assert set(first) == {"id", "first_name", "last_name", "full_name", "mrn", "primary_diagnosis", "created_at"}
    assert first["full_name"] == "John Adams"
    assert body["results"][2]["full_name"] == "John A. Smith"
    assert first["id"] == str(UUID(int=2))
    assert first["mrn"] == "000001" and first["primary_diagnosis"] is None
    assert [p["mrn"] for p in body["results"][:3]] == ["000001", "000000", "000002"]


def test_filtered_second_page(client):
    body = client.get("/patients", params={"search": "  sMi  ", "page": 2, "page_size": 10}).json()
    assert (body["count"], body["page"], body["page_size"]) == (21, 2, 10)
    assert [p["mrn"] for p in body["results"]] == [f"{i:06d}" for i in range(12, 22)]


@pytest.mark.parametrize("search,count", [
    ("John A. Smith", 1), ("John Smith", 20), ("   ", 23), ("missing", 0), ("%", 0), ("_", 0),
])
def test_full_name_search(client, search, count):
    response = client.get("/patients", params={"search": search})
    assert response.status_code == 200
    assert response.json()["count"] == count
    assert len(response.json()["results"]) == min(20, count)


def test_page_beyond_results(client):
    response = client.get("/patients", params={"page": 10**20})
    assert response.status_code == 200
    assert response.json() == {"count": 23, "page": 10**20, "page_size": 20, "results": []}


@pytest.mark.parametrize("params", [{"page": 0}, {"page": "abc"}, {"page_size": 0}, {"page_size": 101}])
def test_invalid_pagination(client, params):
    response = client.get("/patients", params=params)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"

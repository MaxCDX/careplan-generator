import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import CarePlan, Order, Patient, Provider

JOHN_ID = "10000000-0000-4000-8000-000000000001"
PROVIDER_ID = "20000000-0000-4000-8000-000000000001"


@pytest.fixture
def listing():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    provider = Provider(id=PROVIDER_ID, name="Fictional Provider", npi="1234567890")
    other = Provider(name="Other Provider", npi="0123456789")
    john = Patient(id=JOHN_ID, first_name="John", last_name="Smith", mrn="123456")
    alice = Patient(id="alice", first_name="Alice", last_name="Jones", mrn="654321")
    db.add_all([provider, other, john, alice])
    db.flush()
    for i in range(25):
        db.add(Order(
            id=f"order-{i:02}", patient_id=john.id if i % 2 == 0 else alice.id,
            provider_id=provider.id if i < 16 else other.id, medication="IVIG", diagnosis="G70.00",
            clinical_notes="Fictional note", status=["queued", "processing", "completed", "failed"][i % 4],
            created_at=datetime(2026, 1, 1) + timedelta(minutes=i),
        ))
    db.commit()
    db.expunge_all()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app), db, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()


def test_default_pagination(listing):
    client, _, _ = listing
    response = client.get("/orders")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"count", "page", "page_size", "results"}
    assert (body["count"], body["page"], body["page_size"]) == (25, 1, 20)
    assert [row["id"] for row in body["results"]] == [f"order-{i:02}" for i in range(24, 4, -1)]


def test_second_page_and_total(listing):
    client, _, _ = listing
    body = client.get("/orders", params={"page": 2, "page_size": 10}).json()
    assert (body["count"], body["page"], body["page_size"]) == (25, 2, 10)
    assert [row["id"] for row in body["results"]] == [f"order-{i:02}" for i in range(14, 4, -1)]


@pytest.mark.parametrize("status", ["queued", "processing", "completed", "failed"])
def test_status_filter_total_before_pagination(listing, status):
    client, _, _ = listing
    body = client.get("/orders", params={"status": status, "page_size": 2}).json()
    assert body["count"] == (7 if status == "queued" else 6)
    assert len(body["results"]) == 2
    assert all(row["status"] == status for row in body["results"])


def test_name_substring_is_case_insensitive_and_trimmed(listing):
    client, _, _ = listing
    body = client.get("/orders", params={"patient_name": "  oHn  "}).json()
    assert body["count"] == 13
    assert all(row["patient"]["first_name"] == "John" for row in body["results"])


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_ignores_filter(listing, name):
    client, _, _ = listing
    assert client.get("/orders", params={"patient_name": name}).json()["count"] == 25


def test_combined_filters_use_and(listing):
    client, _, _ = listing
    body = client.get("/orders", params={"status": "completed", "patient_name": "john", "page_size": 2}).json()
    assert body["count"] == 6
    assert len(body["results"]) == 2
    assert all(row["status"] == "completed" and row["patient"]["first_name"] == "John" for row in body["results"])
    assert client.get("/orders", params={"status": "failed", "patient_name": "john"}).json()["count"] == 0


def test_no_matching_records(listing):
    client, _, _ = listing
    assert client.get("/orders", params={"patient_name": "missing"}).json() == {
        "count": 0, "page": 1, "page_size": 20, "results": [],
    }


def test_page_beyond_results(listing):
    client, _, _ = listing
    response = client.get("/orders", params={"page": 100})
    assert response.status_code == 200
    assert response.json() == {"count": 25, "page": 100, "page_size": 20, "results": []}


@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": "abc"}, {"page": "1.5"}, {"page": ""},
    {"page_size": 0}, {"page_size": -1}, {"page_size": 101}, {"page_size": "abc"},
    {"status": "pending"}, {"status": "done"}, {"status": "pending_dispatch"},
    {"status": "unknown"}, {"status": ""},
])
def test_invalid_query_uses_existing_validation_envelope(listing, params):
    client, _, engine = listing
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = client.get("/orders", params=params)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert response.status_code == 400
    assert response.json()["status"] == "error"
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["message"] == "Invalid request input."
    assert isinstance(response.json()["detail"], list)
    assert statements == []


def test_serialization_preserved_and_query_is_paginated(listing):
    client, db, engine = listing
    db.add(CarePlan(order_id="order-22", care_plan_content="Generated content", model="mock"))
    db.add(CarePlan(order_id="order-24", care_plan_content="Hidden content", model="mock"))
    db.commit()
    db.expunge_all()
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append((statement, parameters))
    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = client.get("/orders", params={"page_size": 3})
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    rows = response.json()["results"]
    assert rows[0]["has_care_plan"] is True
    assert rows[0]["care_plan_content"] is None
    assert rows[2]["care_plan_content"] == "Generated content"
    assert rows[2] == client.get("/orders/order-22").json()
    assert len(statements) == 2  # COUNT and page SELECT, no serializer lazy loads.
    count_sql, _ = statements[0]
    page_sql, parameters = statements[1]
    assert "count(" in count_sql.lower()
    assert "limit" not in count_sql.lower() and "order by" not in count_sql.lower()
    assert "LIMIT" in page_sql and "OFFSET" in page_sql
    assert parameters[-2:] == (3, 0)


def test_equal_timestamps_have_deterministic_order(listing):
    client, db, _ = listing
    db.query(Order).update({Order.created_at: datetime(2026, 1, 1)})
    db.commit()
    first = client.get("/orders", params={"page_size": 2}).json()["results"]
    second = client.get("/orders", params={"page_size": 2, "page": 2}).json()["results"]
    assert [row["id"] for row in first + second] == ["order-24", "order-23", "order-22", "order-21"]


@pytest.mark.parametrize("name", ["%", "_", "/"])
def test_search_wildcards_are_literal(listing, name):
    client, _, _ = listing
    assert client.get("/orders", params={"patient_name": name}).json()["count"] == 0


def test_empty_database(listing):
    client, db, _ = listing
    db.query(Order).delete()
    db.commit()
    assert client.get("/orders").json() == {"count": 0, "page": 1, "page_size": 20, "results": []}


def test_maximum_page_size_is_allowed(listing):
    client, _, _ = listing
    response = client.get("/orders", params={"page_size": 100})
    assert response.status_code == 200
    assert len(response.json()["results"]) == 25


def test_literal_wildcards_match_names_containing_them(listing):
    client, db, _ = listing
    db.query(Patient).filter(Patient.id == JOHN_ID).update({Patient.first_name: "John %_/ Example"})
    db.commit()
    body = client.get("/orders", params={"patient_name": "%_/"}).json()
    assert body["count"] == 13
    assert all(row["patient"]["first_name"] == "John %_/ Example" for row in body["results"])


def test_combined_filters_and_offset_are_applied_in_sql(listing):
    client, _, engine = listing
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append((statement, parameters))
    event.listen(engine, "before_cursor_execute", capture)
    try:
        body = client.get("/orders", params={"page": 2, "page_size": 2, "status": "completed", "patient_name": "john"}).json()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert body["count"] == 6
    assert [row["id"] for row in body["results"]] == ["order-14", "order-10"]
    assert len(statements) == 2
    for statement, parameters in statements:
        assert "JOIN patients" in statement
        assert "orders.status =" in statement and "patients.first_name" in statement
        assert "completed" in parameters and "%john%" in parameters
    assert statements[1][1][-2:] == (2, 2)


def test_openapi_describes_list_contract():
    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/orders"]["get"]
    parameters = {item["name"]: item["schema"] for item in operation["parameters"]}
    assert parameters["page"]["default"] == 1
    assert parameters["page"]["minimum"] == 1
    assert parameters["page_size"]["default"] == 20
    assert parameters["page_size"]["maximum"] == 100
    assert parameters["status"]["anyOf"][0]["enum"] == ["queued", "processing", "completed", "failed"]
    assert "400" in operation["responses"]

    for name in ("patient_id", "provider_id"):
        assert parameters[name]["anyOf"][0]["format"] == "uuid"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/OrderListResponse")


@pytest.mark.parametrize("filters,expected", [
    ({"patient_id": JOHN_ID}, range(24, -1, -2)),
    ({"provider_id": PROVIDER_ID}, range(15, -1, -1)),
    ({"patient_id": PROVIDER_ID}, []),
    ({"provider_id": JOHN_ID}, []),
])
def test_order_id_filters(listing, filters, expected):
    client, _, _ = listing
    response = client.get("/orders", params=filters)
    assert response.status_code == 200
    assert response.json()["count"] == len(expected)
    assert [row["id"] for row in response.json()["results"]] == [f"order-{i:02}" for i in expected]


def test_order_id_filters_combined_before_pagination(listing):
    client, _, _ = listing
    filters = {"patient_id": JOHN_ID, "provider_id": PROVIDER_ID, "status": "queued",
               "patient_name": "smith", "page": 2, "page_size": 2}
    body = client.get("/orders", params=filters).json()
    assert body["count"] == 4
    assert [row["id"] for row in body["results"]] == ["order-04", "order-00"]


@pytest.mark.parametrize("name", ["patient_id", "provider_id"])
def test_invalid_id_filter(listing, name):
    client, _, _ = listing
    response = client.get("/orders", params={name: "1"})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"

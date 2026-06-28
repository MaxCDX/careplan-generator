import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def post_external_order(source: str, payload: dict):
    app.dependency_overrides[get_db] = lambda: object()
    try:
        client = TestClient(app, raise_server_exceptions=False)
        return client.post(f"/external-orders/{source}", json=payload)
    finally:
        app.dependency_overrides.clear()


def assert_invalid_external_order(response) -> None:
    assert response.status_code == 400
    assert response.json() == {
        "status": "error",
        "code": "INVALID_EXTERNAL_ORDER",
        "message": "Invalid external order input.",
        "detail": {},
    }


def test_unsupported_source_returns_safe_bad_request_envelope():
    response = post_external_order("unknown", {})

    assert_invalid_external_order(response)
    assert "unknown" not in response.text


def test_malformed_pharmacorp_xml_returns_safe_bad_request_envelope():
    response = post_external_order(
        "pharmacorp",
        {"xml": "<CareOrderRequest>raw-parser-detail"},
    )

    assert_invalid_external_order(response)
    assert "raw-parser-detail" not in response.text


def test_missing_enterprise_spreadsheet_returns_safe_bad_request_envelope(tmp_path):
    missing_path = tmp_path / "sensitive-missing-workbook.xlsx"

    response = post_external_order(
        "enterprise_spreadsheet",
        {"file_path": str(missing_path)},
    )

    assert_invalid_external_order(response)
    assert str(missing_path) not in response.text


def test_bad_clinic_b_dob_returns_safe_bad_request_envelope():
    response = post_external_order(
        "clinic_b",
        {"pt": {"dob": "raw-invalid-dob"}},
    )

    assert_invalid_external_order(response)
    assert "raw-invalid-dob" not in response.text

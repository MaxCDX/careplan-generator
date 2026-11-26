import os

from openpyxl import Workbook

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def enterprise_spreadsheet_payload(tmp_path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        [
            "Patient ID",
            "First Name",
            "Last Name",
            "Date of Birth",
            "Provider",
            "Provider NPI",
            "Primary Diagnosis",
            "Secondary Diagnoses",
            "Medication",
            "Dose",
            "Frequency",
            "NDC",
            "Allergies",
            "Current Medications",
            "Weight",
            "Notes",
        ]
    )
    worksheet.append(
        [
            "678901",
            "Lena",
            "Patel",
            "1990-04-12",
            "Dr. Anita Rao",
            "3344556677",
            "M06.9",
            "I10;E78.5",
            "Humira",
            "40mg",
            "Every Other Week",
            "0074-4339-02",
            "Shellfish;Latex",
            "Methotrexate;Folic acid",
            68,
            "Persistent joint swelling despite current therapy.",
        ]
    )
    file_path = tmp_path / "enterprise_order.xlsx"
    workbook.save(file_path)
    return {"file_path": str(file_path)}


def test_enterprise_spreadsheet_parse_returns_row_dict(tmp_path):
    from app.external_orders.adapters.enterprise_spreadsheet import EnterpriseSpreadsheetAdapter

    parsed = EnterpriseSpreadsheetAdapter().parse(enterprise_spreadsheet_payload(tmp_path))

    assert parsed["Patient ID"] == "678901"


def test_enterprise_spreadsheet_adapter_returns_expected_order_create_fields(tmp_path):
    from app.external_orders.adapters.enterprise_spreadsheet import EnterpriseSpreadsheetAdapter

    order = EnterpriseSpreadsheetAdapter().normalize(enterprise_spreadsheet_payload(tmp_path))

    assert order.patient_first_name == "Lena"
    assert order.patient_last_name == "Patel"
    assert order.patient_middle_name is None
    assert order.mrn == "678901"
    assert order.patient_date_of_birth.isoformat() == "1990-04-12"
    assert order.provider_npi == "3344556677"
    assert order.diagnosis == "M06.9"
    assert order.medication == "Humira"
    assert "I10" in order.clinical_notes
    assert "Shellfish" in order.clinical_notes
    assert "Methotrexate" in order.clinical_notes
    assert "Dose/frequency: 40mg; Every Other Week" in order.clinical_notes

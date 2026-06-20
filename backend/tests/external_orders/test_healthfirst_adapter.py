import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def healthfirst_payload():
    return {
        "row": (
            "ORDER_DATE,FACILITY,PATIENT_NO,LAST_NAME,FIRST_NAME,DOB,NPI,PROVIDER,"
            "ICD10_PRIMARY,ICD10_SECONDARY,MEDICATION,DOSAGE,FREQUENCY,NDC,ALLERGIES,"
            "CURRENT_MEDS,WEIGHT_KG,NOTES\n"
            '2025-01-18,HF_WEST,567890,Garcia,Maria,1988-06-15,2233445566,'
            'Dr. David Kim,G35,"I10;E11.9",Ocrevus,600mg,Every 6 Months,'
            '50242-150-01,"Latex;Peanuts","Vitamin D;Baclofen",72,'
            '"Recent MRI demonstrates active lesions."'
        )
    }


def test_healthfirst_parse_returns_csv_row_dict():
    from app.external_orders.adapters.healthfirst import HealthFirstAdapter

    parsed = HealthFirstAdapter().parse(healthfirst_payload())

    assert parsed["PATIENT_NO"] == "567890"


def test_healthfirst_adapter_returns_expected_order_create_fields():
    from app.external_orders.adapters.healthfirst import HealthFirstAdapter

    order = HealthFirstAdapter().normalize(healthfirst_payload())

    assert order.patient_name == "Maria Garcia"
    assert order.mrn == "567890"
    assert order.patient_dob == "1988-06-15"
    assert order.provider_npi == "2233445566"
    assert order.diagnosis == "G35"
    assert order.medication == "Ocrevus"
    assert "I10" in order.clinical_notes
    assert "Latex" in order.clinical_notes
    assert "Vitamin D" in order.clinical_notes

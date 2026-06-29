import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def clinic_b_payload():
    return {
        "order_info": {
            "created": "01/15/2025 2:30 PM",
            "src": "DOWNTOWN_CLINIC",
        },
        "pt": {
            "mrn": "234567",
            "fname": "Jane",
            "lname": "Smith",
            "mi": "A",
            "dob": "03/22/1985",
            "gender": "F",
            "wt": 65,
            "wt_unit": "kg",
        },
        "provider": {
            "name": "Dr. Emily Johnson",
            "npi_num": "0987654321",
        },
        "dx": {
            "primary": "G70.00",
            "secondary": ["E11.9", "I10"],
        },
        "rx": {
            "med_name": "Gamunex-C",
            "ndc": "13533-0800-20",
            "dosage": "32.5g",
            "freq": "every day",
        },
        "allergies": ["Penicillin", "Sulfa"],
        "med_hx": ["Metformin 500mg twice daily"],
        "clinical_notes": "Patient presents with progressive weakness.",
    }


def test_clinic_b_parse_returns_payload_as_is():
    from app.external_orders.adapters.clinic_b import ClinicBAdapter

    payload = clinic_b_payload()

    assert ClinicBAdapter().parse(payload) is payload


def test_clinic_b_adapter_returns_expected_order_create_fields():
    from app.external_orders.adapters.clinic_b import ClinicBAdapter

    order = ClinicBAdapter().normalize(clinic_b_payload())

    assert order.patient_name == "Jane A Smith"
    assert order.mrn == "234567"
    assert order.patient_dob == "1985-03-22"
    assert order.provider_name == "Dr. Emily Johnson"
    assert order.provider_npi == "0987654321"
    assert order.diagnosis == "G70.00"
    assert order.medication == "Gamunex-C"
    assert "Secondary diagnoses: E11.9, I10" in order.clinical_notes
    assert "Dosage/frequency: 32.5g; every day" in order.clinical_notes

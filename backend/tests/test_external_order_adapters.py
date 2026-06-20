import os

import pytest

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


def pharmacorp_payload():
    return {
        "xml": """<?xml version="1.0" encoding="UTF-8"?>
<CareOrderRequest>
    <RequestMetadata>
        <SourceSystem>PharmaCorp_Portal</SourceSystem>
        <RequestTimestamp>2025-01-15T14:30:52Z</RequestTimestamp>
        <RequestId>REQ-2025-00012345</RequestId>
    </RequestMetadata>
    <PatientInformation>
        <MedicalRecordNumber>345678</MedicalRecordNumber>
        <PatientName>
            <FirstName>Robert</FirstName>
            <MiddleName>James</MiddleName>
            <LastName>Williams</LastName>
        </PatientName>
        <DateOfBirth>1972-11-30</DateOfBirth>
        <Gender>Male</Gender>
        <BodyWeight>
            <Value>88</Value>
            <Unit>Kilograms</Unit>
        </BodyWeight>
    </PatientInformation>
    <PrescriberInformation>
        <FullName>Dr. Michael Chen</FullName>
        <NPINumber>5678901234</NPINumber>
        <Facility>University Medical Center</Facility>
    </PrescriberInformation>
    <DiagnosisList>
        <PrimaryDiagnosis>
            <ICDCode>G70.01</ICDCode>
            <Description>Myasthenia gravis with exacerbation</Description>
        </PrimaryDiagnosis>
        <SecondaryDiagnoses>
            <Diagnosis>
                <ICDCode>I10</ICDCode>
                <Description>Essential hypertension</Description>
            </Diagnosis>
        </SecondaryDiagnoses>
    </DiagnosisList>
    <MedicationOrder>
        <DrugName>Octagam</DrugName>
        <NDCCode>67467-0843-01</NDCCode>
        <OrderedDose>
            <Amount>44</Amount>
            <Unit>grams</Unit>
        </OrderedDose>
        <Frequency>Once daily</Frequency>
    </MedicationOrder>
    <AllergyInformation>
        <HasKnownAllergies>false</HasKnownAllergies>
        <AllergyList />
    </AllergyInformation>
    <MedicationHistory>
        <Medication>
            <MedicationName>Pyridostigmine</MedicationName>
            <Dosage>60 mg</Dosage>
            <Route>Oral</Route>
            <Frequency>Every 6 hours as needed</Frequency>
        </Medication>
    </MedicationHistory>
    <ClinicalDocumentation>
        <DocumentType>ProgressNote</DocumentType>
        <DocumentDate>2025-01-14</DocumentDate>
        <AuthoringProvider>Dr. Michael Chen</AuthoringProvider>
        <NarrativeText>58 y/o male with known MG presenting with acute exacerbation.</NarrativeText>
    </ClinicalDocumentation>
</CareOrderRequest>
""",
    }


def test_factory_returns_expected_adapter_types():
    from app.external_orders.adapters.clinic_b import ClinicBAdapter
    from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter
    from app.external_orders.factory import get_external_order_adapter

    assert isinstance(get_external_order_adapter(" clinic_b "), ClinicBAdapter)
    assert isinstance(get_external_order_adapter("PHARMACORP"), PharmaCorpAdapter)


def test_factory_rejects_unsupported_source():
    from app.external_orders.factory import get_external_order_adapter

    with pytest.raises(ValueError, match="Unsupported external order source: unknown"):
        get_external_order_adapter("unknown")


def test_clinic_b_parse_returns_payload_as_is():
    from app.external_orders.adapters.clinic_b import ClinicBAdapter

    payload = clinic_b_payload()

    assert ClinicBAdapter().parse(payload) is payload


def test_pharmacorp_parse_returns_xml_root_element():
    from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter

    root = PharmaCorpAdapter().parse(pharmacorp_payload())

    assert root.tag == "CareOrderRequest"


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


def test_pharmacorp_adapter_returns_expected_order_create_fields():
    from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter

    order = PharmaCorpAdapter().normalize(pharmacorp_payload())

    assert order.patient_name == "Robert James Williams"
    assert order.mrn == "345678"
    assert order.patient_dob == "1972-11-30"
    assert order.provider_name == "Dr. Michael Chen"
    assert order.provider_npi == "5678901234"
    assert order.diagnosis == "G70.01"
    assert order.medication == "Octagam"
    assert "Secondary diagnoses:" in order.clinical_notes
    assert "- I10 - Essential hypertension" in order.clinical_notes
    assert "Dose/frequency: 44 grams; Once daily" in order.clinical_notes

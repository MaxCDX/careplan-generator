import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


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


def test_pharmacorp_parse_returns_xml_root_element():
    from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter

    root = PharmaCorpAdapter().parse(pharmacorp_payload())

    assert root.tag == "CareOrderRequest"


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

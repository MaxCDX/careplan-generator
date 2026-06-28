from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from app.external_orders.adapters.base import BaseIntakeAdapter
from app.external_orders.adapters.utils import append_note_if_present, build_clinical_notes, join_nonblank_parts
from app.external_orders.errors import ExternalOrderInputError
from app.orders.schemas import OrderCreate


class PharmaCorpAdapter(BaseIntakeAdapter):
    """Normalize PharmaCorp XML payloads into OrderCreate."""

    def parse(self, payload: dict):
        """Parse PharmaCorp's XML payload into an ElementTree root."""
        raw_xml = payload.get("xml", "")
        try:
            return ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as exc:
            raise ExternalOrderInputError("Invalid PharmaCorp XML payload.") from exc

    def transform(self, root) -> OrderCreate:
        """Transform a parsed PharmaCorp XML root into OrderCreate.

        Expected learning-project payload shape:
            {"xml": "..."}

        This adapter owns PharmaCorp-specific XML parsing and field mapping only.
        Validation, duplicate detection, and workflow dispatch stay in the existing
        OrderCreate and order service layers.
        """
        name_parts = [
            require_xml_text(root, "./PatientInformation/PatientName/FirstName"),
            root.findtext("./PatientInformation/PatientName/MiddleName", default=""),
            require_xml_text(root, "./PatientInformation/PatientName/LastName"),
        ]
        patient_name = join_nonblank_parts(name_parts)
        mrn = require_xml_text(root, "./PatientInformation/MedicalRecordNumber")
        patient_dob = require_xml_text(root, "./PatientInformation/DateOfBirth")
        provider_name = require_xml_text(root, "./PrescriberInformation/FullName")
        provider_npi = require_xml_text(root, "./PrescriberInformation/NPINumber")
        diagnosis = require_xml_text(root, "./DiagnosisList/PrimaryDiagnosis/ICDCode")
        medication = require_xml_text(root, "./MedicationOrder/DrugName")

        clinical_note_parts = []

        narrative_text = root.findtext("./ClinicalDocumentation/NarrativeText", default="").strip()
        if narrative_text:
            clinical_note_parts.append(narrative_text)

        source_system = root.findtext("./RequestMetadata/SourceSystem", default="").strip()
        append_note_if_present(clinical_note_parts, "Source system", source_system)

        request_id = root.findtext("./RequestMetadata/RequestId", default="").strip()
        append_note_if_present(clinical_note_parts, "Request ID", request_id)

        request_timestamp = root.findtext("./RequestMetadata/RequestTimestamp", default="").strip()
        append_note_if_present(clinical_note_parts, "Request timestamp", request_timestamp)

        gender = root.findtext("./PatientInformation/Gender", default="").strip()
        append_note_if_present(clinical_note_parts, "Gender", gender)

        weight_value = root.findtext("./PatientInformation/BodyWeight/Value", default="").strip()
        weight_unit = root.findtext("./PatientInformation/BodyWeight/Unit", default="").strip()
        weight_parts = [part for part in [weight_value, weight_unit] if part]
        if weight_parts:
            clinical_note_parts.append(f"Weight: {' '.join(weight_parts)}")

        facility = root.findtext("./PrescriberInformation/Facility", default="").strip()
        append_note_if_present(clinical_note_parts, "Facility", facility)

        primary_diagnosis_description = root.findtext(
            "./DiagnosisList/PrimaryDiagnosis/Description",
            default="",
        ).strip()
        if primary_diagnosis_description:
            clinical_note_parts.append(f"Primary diagnosis description: {primary_diagnosis_description}")

        secondary_diagnosis_parts = []
        for secondary_diagnosis in root.findall("./DiagnosisList/SecondaryDiagnoses/Diagnosis"):
            secondary_code = secondary_diagnosis.findtext("ICDCode", default="").strip()
            secondary_description = secondary_diagnosis.findtext("Description", default="").strip()
            secondary_parts = [part for part in [secondary_code, secondary_description] if part]
            if secondary_parts:
                secondary_diagnosis_parts.append(" - ".join(secondary_parts))
        if secondary_diagnosis_parts:
            clinical_note_parts.append("Secondary diagnoses:")
            for secondary_diagnosis_part in secondary_diagnosis_parts:
                clinical_note_parts.append(f"- {secondary_diagnosis_part}")

        ndc = root.findtext("./MedicationOrder/NDCCode", default="").strip()
        append_note_if_present(clinical_note_parts, "NDC", ndc)

        dose_amount = root.findtext("./MedicationOrder/OrderedDose/Amount", default="").strip()
        dose_unit = root.findtext("./MedicationOrder/OrderedDose/Unit", default="").strip()
        frequency = root.findtext("./MedicationOrder/Frequency", default="").strip()
        dose_parts = [part for part in [dose_amount, dose_unit] if part]
        dose_frequency_parts = []
        if dose_parts:
            dose_frequency_parts.append(" ".join(dose_parts))
        if frequency:
            dose_frequency_parts.append(frequency)
        if dose_frequency_parts:
            clinical_note_parts.append(f"Dose/frequency: {'; '.join(dose_frequency_parts)}")

        has_known_allergies = root.findtext("./AllergyInformation/HasKnownAllergies", default="").strip()
        allergy_values = []
        for allergy in root.findall("./AllergyInformation/AllergyList/Allergy"):
            allergy_text = (allergy.text or "").strip()
            allergy_name = allergy.findtext("Name", default="").strip()
            allergy_values.append(allergy_text or allergy_name)
        allergy_values = [allergy_value for allergy_value in allergy_values if allergy_value]
        if has_known_allergies or allergy_values:
            allergy_note = f"Has known allergies: {has_known_allergies}" if has_known_allergies else "Allergies:"
            if allergy_values:
                allergy_note = f"{allergy_note} {', '.join(allergy_values)}"
            clinical_note_parts.append(allergy_note)

        medication_history_parts = []
        for medication_history_item in root.findall("./MedicationHistory/Medication"):
            medication_name = medication_history_item.findtext("MedicationName", default="").strip()
            dosage = medication_history_item.findtext("Dosage", default="").strip()
            route = medication_history_item.findtext("Route", default="").strip()
            med_frequency = medication_history_item.findtext("Frequency", default="").strip()
            medication_parts = [part for part in [medication_name, dosage, route, med_frequency] if part]
            if medication_parts:
                medication_history_parts.append(" - ".join(medication_parts))
        if medication_history_parts:
            clinical_note_parts.append("Medication history:")
            for medication_history_part in medication_history_parts:
                clinical_note_parts.append(f"- {medication_history_part}")

        document_type = root.findtext("./ClinicalDocumentation/DocumentType", default="").strip()
        document_date = root.findtext("./ClinicalDocumentation/DocumentDate", default="").strip()
        authoring_provider = root.findtext("./ClinicalDocumentation/AuthoringProvider", default="").strip()
        document_metadata_parts = []
        if document_type:
            document_metadata_parts.append(f"type={document_type}")
        if document_date:
            document_metadata_parts.append(f"date={document_date}")
        if authoring_provider:
            document_metadata_parts.append(f"author={authoring_provider}")
        if document_metadata_parts:
            clinical_note_parts.append(f"Clinical document metadata: {', '.join(document_metadata_parts)}")

        clinical_notes = build_clinical_notes(clinical_note_parts)

        return OrderCreate(
            patient_name=patient_name,
            patient_dob=patient_dob,
            mrn=mrn,
            provider_name=provider_name,
            provider_npi=provider_npi,
            diagnosis=diagnosis,
            medication=medication,
            clinical_notes=clinical_notes,
        )


def require_xml_text(root: Element, path: str) -> str:
    """Return required XML text for a simple ElementTree path."""
    element = root.find(path)
    if element is None or element.text is None or not element.text.strip():
        raise ExternalOrderInputError(f"Missing required XML field: {path}")

    return element.text.strip()

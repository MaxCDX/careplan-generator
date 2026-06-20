from datetime import datetime

from app.external_orders.adapters.base import BaseIntakeAdapter
from app.orders.schemas import OrderCreate


class ClinicBAdapter(BaseIntakeAdapter):
    """Normalize Clinic B JSON payloads into OrderCreate."""

    def parse(self, payload: dict):
        """Return Clinic B's JSON payload as-is for this minimal refactor."""
        return payload

    def transform(self, parsed) -> OrderCreate:
        """Transform a parsed Clinic B payload into OrderCreate.

        This adapter owns Clinic B's source-specific field mapping only.
        Validation, duplicate detection, and workflow dispatch stay in the existing
        OrderCreate and order service layers.
        """
        order_info = parsed.get("order_info", {})
        patient = parsed.get("pt", {})
        provider = parsed.get("provider", {})
        diagnosis_info = parsed.get("dx", {})
        prescription = parsed.get("rx", {})

        name_parts = [
            patient.get("fname", ""),
            patient.get("mi", ""),
            patient.get("lname", ""),
        ]
        patient_name = " ".join(part.strip() for part in name_parts if part and part.strip())
        patient_mrn = patient.get("mrn", "")
        patient_dob = parse_clinic_b_dob(patient.get("dob"))
        provider_name = provider.get("name", "")
        provider_npi = provider.get("npi_num", "")
        diagnosis = diagnosis_info.get("primary", "")
        medication = prescription.get("med_name", "")

        clinical_note_parts = []

        original_notes = parsed.get("clinical_notes", "")
        if original_notes:
            clinical_note_parts.append(str(original_notes).strip())

        source_system = order_info.get("src", "")
        if source_system:
            clinical_note_parts.append(f"Source system: {source_system}")

        source_created_time = order_info.get("created", "")
        if source_created_time:
            clinical_note_parts.append(f"Source created time: {source_created_time}")

        gender = patient.get("gender", "")
        if gender:
            clinical_note_parts.append(f"Gender: {gender}")

        weight = patient.get("wt")
        weight_unit = patient.get("wt_unit", "")
        if weight:
            clinical_note_parts.append(f"Weight: {weight} {weight_unit}".strip())

        allergies = parsed.get("allergies", [])
        if allergies:
            clinical_note_parts.append(f"Allergies: {', '.join(str(item) for item in allergies)}")

        med_hx = parsed.get("med_hx", [])
        if med_hx:
            clinical_note_parts.append("Medication history:")
            for medication_history_item in med_hx:
                clinical_note_parts.append(f"- {medication_history_item}")

        secondary_diagnoses = diagnosis_info.get("secondary", [])
        if secondary_diagnoses:
            clinical_note_parts.append(f"Secondary diagnoses: {', '.join(str(item) for item in secondary_diagnoses)}")

        ndc = prescription.get("ndc", "")
        if ndc:
            clinical_note_parts.append(f"NDC: {ndc}")

        dosage = prescription.get("dosage", "")
        frequency = prescription.get("freq", "")
        dosage_frequency_parts = [part for part in [dosage, frequency] if part]
        if dosage_frequency_parts:
            clinical_note_parts.append(f"Dosage/frequency: {'; '.join(dosage_frequency_parts)}")

        clinical_notes = "\n".join(part for part in clinical_note_parts if part)

        return OrderCreate(
            patient_name=patient_name,
            patient_dob=patient_dob,
            mrn=patient_mrn,
            provider_name=provider_name,
            provider_npi=provider_npi,
            diagnosis=diagnosis,
            medication=medication,
            clinical_notes=clinical_notes,
        )


def parse_clinic_b_dob(value):
    """Parse Clinic B DOB values into YYYY-MM-DD strings for OrderCreate."""
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cleaned, date_format).date().isoformat()
            except ValueError:
                pass

    raise ValueError("Clinic B DOB must be an MM/DD/YYYY or YYYY-MM-DD string for this starter exercise.")

import csv
from io import StringIO

from app.external_orders.adapters.base import BaseIntakeAdapter
from app.external_orders.adapters.utils import append_note_if_present, build_clinical_notes, join_nonblank_parts
from app.external_orders.errors import ExternalOrderInputError
from app.orders.schemas import OrderCreate


class HealthFirstAdapter(BaseIntakeAdapter):
    """Normalize HealthFirst Hospital CSV payloads into OrderCreate."""

    def parse(self, payload: dict):
        """Parse one CSV row wrapped in a JSON payload into a dict."""
        raw_row = payload.get("row")
        if not raw_row:
            raise ExternalOrderInputError("HealthFirst payload must include row.")

        reader = csv.DictReader(StringIO(raw_row))
        parsed = next(reader, None)
        if not parsed:
            raise ExternalOrderInputError("HealthFirst payload must include one data row.")

        return parsed

    def transform(self, parsed) -> OrderCreate:
        """Transform a parsed HealthFirst row into OrderCreate."""
        name_parts = [
            parsed.get("FIRST_NAME", ""),
            parsed.get("LAST_NAME", ""),
        ]
        patient_name = join_nonblank_parts(name_parts)

        clinical_note_parts = []

        notes = parsed.get("NOTES", "")
        if notes:
            clinical_note_parts.append(str(notes).strip())

        clinical_note_parts.append("Source system: HealthFirst Hospital")

        facility = parsed.get("FACILITY", "")
        append_note_if_present(clinical_note_parts, "Facility", facility)

        order_date = parsed.get("ORDER_DATE", "")
        append_note_if_present(clinical_note_parts, "Order date", order_date)

        secondary_diagnoses = _split_semicolon_values(parsed.get("ICD10_SECONDARY", ""))
        if secondary_diagnoses:
            clinical_note_parts.append(f"Secondary diagnoses: {', '.join(secondary_diagnoses)}")

        ndc = parsed.get("NDC", "")
        append_note_if_present(clinical_note_parts, "NDC", ndc)

        dosage = parsed.get("DOSAGE", "")
        frequency = parsed.get("FREQUENCY", "")
        dosage_frequency_parts = [part for part in [dosage, frequency] if part]
        if dosage_frequency_parts:
            clinical_note_parts.append(f"Dose/frequency: {'; '.join(dosage_frequency_parts)}")

        allergies = _split_semicolon_values(parsed.get("ALLERGIES", ""))
        if allergies:
            clinical_note_parts.append(f"Allergies: {', '.join(allergies)}")

        current_meds = _split_semicolon_values(parsed.get("CURRENT_MEDS", ""))
        if current_meds:
            clinical_note_parts.append(f"Current medications: {', '.join(current_meds)}")

        weight = parsed.get("WEIGHT_KG", "")
        if weight:
            clinical_note_parts.append(f"Weight: {weight} kg")

        clinical_notes = build_clinical_notes(clinical_note_parts)

        return OrderCreate(
            patient_name=patient_name,
            patient_dob=parsed.get("DOB", ""),
            mrn=parsed.get("PATIENT_NO", ""),
            provider_name=parsed.get("PROVIDER", ""),
            provider_npi=parsed.get("NPI", ""),
            diagnosis=parsed.get("ICD10_PRIMARY", ""),
            medication=parsed.get("MEDICATION", ""),
            clinical_notes=clinical_notes,
        )


def _split_semicolon_values(value) -> list[str]:
    if not value:
        return []

    return [part.strip() for part in str(value).split(";") if part.strip()]

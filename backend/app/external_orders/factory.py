from app.external_orders.adapters.base import BaseIntakeAdapter
from app.external_orders.adapters.clinic_b import ClinicBAdapter
from app.external_orders.adapters.enterprise_spreadsheet import EnterpriseSpreadsheetAdapter
from app.external_orders.adapters.healthfirst import HealthFirstAdapter
from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter
from app.external_orders.errors import ExternalOrderInputError


def get_external_order_adapter(source: str) -> BaseIntakeAdapter:
    """Return the adapter for a supported external order source."""
    normalized_source = source.strip().lower()

    if normalized_source == "clinic_b":
        return ClinicBAdapter()

    if normalized_source == "pharmacorp":
        return PharmaCorpAdapter()

    if normalized_source == "healthfirst":
        return HealthFirstAdapter()

    if normalized_source == "enterprise_spreadsheet":
        return EnterpriseSpreadsheetAdapter()

    raise ExternalOrderInputError(f"Unsupported external order source: {source}")

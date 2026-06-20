import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_factory_returns_expected_adapter_types():
    from app.external_orders.adapters.clinic_b import ClinicBAdapter
    from app.external_orders.adapters.enterprise_spreadsheet import EnterpriseSpreadsheetAdapter
    from app.external_orders.adapters.healthfirst import HealthFirstAdapter
    from app.external_orders.adapters.pharmacorp import PharmaCorpAdapter
    from app.external_orders.factory import get_external_order_adapter

    assert isinstance(get_external_order_adapter(" clinic_b "), ClinicBAdapter)
    assert isinstance(get_external_order_adapter("PHARMACORP"), PharmaCorpAdapter)
    assert isinstance(get_external_order_adapter("healthfirst"), HealthFirstAdapter)
    assert isinstance(get_external_order_adapter("enterprise_spreadsheet"), EnterpriseSpreadsheetAdapter)


def test_factory_rejects_unsupported_source():
    from app.external_orders.factory import get_external_order_adapter

    with pytest.raises(ValueError, match="Unsupported external order source: unknown"):
        get_external_order_adapter("unknown")

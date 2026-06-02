import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.orders import service
from app.orders.schemas import OrderCreate, WarningResponse


def order_create(**overrides):
    payload = {
        "patient_name": "Test Patient",
        "patient_dob": "1979-06-08",
        "mrn": "123456",
        "provider_name": "Dr. Test",
        "provider_npi": "1234567890",
        "diagnosis": "G70.00",
        "medication": "IVIG",
        "clinical_notes": "Fictional clinical note.",
    }
    payload.update(overrides)
    return OrderCreate(**payload)


def patient(*, name="Test Patient", mrn="123456", dob="1979-06-08"):
    return SimpleNamespace(id="patient-1", name=name, mrn=mrn, dob=dob)


def order():
    return SimpleNamespace(id="order-1")


class FakeGenerateCarePlanTask:
    dispatched_order_ids = []

    @classmethod
    def delay(cls, order_id):
        cls.dispatched_order_ids.append(order_id)


def patch_clean_dependencies(monkeypatch, *, existing_patient=None, same_identity_patient=None):
    created_orders = []
    same_identity_calls = []

    def fake_get_patient_by_name_and_dob(db, *, name, dob):
        same_identity_calls.append({"name": name, "dob": dob})
        return same_identity_patient

    def fake_create_order(db, data):
        created_order = order()
        created_orders.append(created_order)
        return created_order

    FakeGenerateCarePlanTask.dispatched_order_ids = []
    monkeypatch.setattr(service.provider_repository, "get_provider_by_npi", lambda db, npi: None)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_mrn", lambda db, mrn: existing_patient)
    monkeypatch.setattr(service.patient_repository, "get_patient_by_name_and_dob", fake_get_patient_by_name_and_dob)
    monkeypatch.setattr(service.repository, "get_latest_order_for_patient_and_medication", lambda db, patient_id, medication: None)
    monkeypatch.setattr(service.repository, "create_order", fake_create_order)
    monkeypatch.setattr(service, "generate_care_plan_task", FakeGenerateCarePlanTask)

    return created_orders, same_identity_calls


def test_existing_same_mrn_same_name_same_dob_proceeds_without_warning(monkeypatch):
    created_orders, same_identity_calls = patch_clean_dependencies(
        monkeypatch,
        existing_patient=patient(),
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create())

    assert result.id == "order-1"
    assert created_orders == [result]
    assert FakeGenerateCarePlanTask.dispatched_order_ids == ["order-1"]
    assert same_identity_calls == []


def test_existing_same_mrn_different_name_returns_warning_without_order_or_dispatch(monkeypatch):
    created_orders, _ = patch_clean_dependencies(
        monkeypatch,
        existing_patient=patient(name="Existing Patient"),
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create(patient_name="Different Patient"))

    assert isinstance(result, WarningResponse)
    assert result.warnings[0].code == "PATIENT_MRN_MISMATCH"
    assert created_orders == []
    assert FakeGenerateCarePlanTask.dispatched_order_ids == []


def test_existing_same_mrn_different_dob_returns_warning_without_order_or_dispatch(monkeypatch):
    created_orders, _ = patch_clean_dependencies(
        monkeypatch,
        existing_patient=patient(dob="1980-01-01"),
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create(patient_dob="1979-06-08"))

    assert isinstance(result, WarningResponse)
    assert result.warnings[0].code == "PATIENT_MRN_MISMATCH"
    assert created_orders == []
    assert FakeGenerateCarePlanTask.dispatched_order_ids == []


def test_same_name_same_dob_different_mrn_returns_warning_without_order_or_dispatch(monkeypatch):
    created_orders, same_identity_calls = patch_clean_dependencies(
        monkeypatch,
        existing_patient=None,
        same_identity_patient=patient(mrn="999999"),
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create(mrn="123456"))

    assert isinstance(result, WarningResponse)
    assert result.warnings[0].code == "PATIENT_POSSIBLE_DUPLICATE"
    assert created_orders == []
    assert FakeGenerateCarePlanTask.dispatched_order_ids == []
    assert same_identity_calls == [{"name": "Test Patient", "dob": "1979-06-08"}]


def test_no_existing_mrn_and_no_same_identity_proceeds_normally(monkeypatch):
    created_orders, same_identity_calls = patch_clean_dependencies(
        monkeypatch,
        existing_patient=None,
        same_identity_patient=None,
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create())

    assert result.id == "order-1"
    assert created_orders == [result]
    assert FakeGenerateCarePlanTask.dispatched_order_ids == ["order-1"]
    assert same_identity_calls == [{"name": "Test Patient", "dob": "1979-06-08"}]


def test_missing_dob_does_not_run_same_identity_duplicate_lookup(monkeypatch):
    created_orders, same_identity_calls = patch_clean_dependencies(
        monkeypatch,
        existing_patient=None,
        same_identity_patient=patient(mrn="999999", dob=None),
    )

    result = service.create_order_and_dispatch_care_plan(object(), order_create(patient_dob=None))

    assert result.id == "order-1"
    assert created_orders == [result]
    assert FakeGenerateCarePlanTask.dispatched_order_ids == ["order-1"]
    assert same_identity_calls == []

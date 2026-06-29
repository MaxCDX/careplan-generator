import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def make_order():
    patient = SimpleNamespace(name="Test Patient", mrn="123456")
    provider = SimpleNamespace(name="Dr. Test", npi="1234567890")
    return SimpleNamespace(
        patient=patient,
        provider=provider,
        medication="IVIG",
        diagnosis="G70.00",
        clinical_notes="Fictional clinical note.",
    )


def test_mock_provider_returns_fixed_care_plan_without_openai_api_key(monkeypatch):
    from app.care_plans import service

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("MOCK_LLM_DELAY_SECS", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    content = service.generate_care_plan_content(make_order(), "test-model")

    assert "Problem list:" in content
    assert "Goals:" in content
    assert "Pharmacist interventions:" in content
    assert "Monitoring plan:" in content
    assert "Mock problem list for local care plan testing." in content


def test_mock_provider_uses_configured_delay(monkeypatch):
    from app.care_plans import service
    from app.llm.services import mock_service

    delays = []

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("MOCK_LLM_DELAY_SECS", "1.5")
    monkeypatch.setattr(mock_service.time, "sleep", lambda delay: delays.append(delay))

    service.generate_care_plan_content(make_order(), "test-model")

    assert delays == [1.5]

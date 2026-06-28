import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_mock_service_returns_deterministic_care_plan_content(monkeypatch):
    from app.llm.services.mock_service import MockLLMService

    monkeypatch.setenv("MOCK_LLM_DELAY_SECS", "0")

    content = MockLLMService().generate("ignored prompt", "ignored-model")

    assert "Problem list:" in content
    assert "Goals:" in content
    assert "Pharmacist interventions:" in content
    assert "Monitoring plan:" in content
    assert "Mock problem list for local care plan testing." in content


def test_mock_service_honors_configured_delay(monkeypatch):
    from app.llm.services import mock_service
    from app.llm.services.mock_service import MockLLMService

    delays = []
    monkeypatch.setenv("MOCK_LLM_DELAY_SECS", "1.5")
    monkeypatch.setattr(mock_service.time, "sleep", lambda delay: delays.append(delay))

    MockLLMService().generate("ignored prompt", "ignored-model")

    assert delays == [1.5]


def test_mock_service_rejects_non_numeric_delay(monkeypatch):
    from app.llm.errors import LLMConfigurationError
    from app.llm.services.mock_service import MockLLMService

    monkeypatch.setenv("MOCK_LLM_DELAY_SECS", "not-a-number")

    with pytest.raises(LLMConfigurationError, match="MOCK_LLM_DELAY_SECS must be a number."):
        MockLLMService().generate("ignored prompt", "ignored-model")

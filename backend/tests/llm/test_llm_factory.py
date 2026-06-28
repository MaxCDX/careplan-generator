import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_factory_returns_mock_service_when_provider_is_mock(monkeypatch):
    from app.llm.factory import get_llm_service
    from app.llm.services.mock_service import MockLLMService

    monkeypatch.setenv("LLM_PROVIDER", "mock")

    assert isinstance(get_llm_service(), MockLLMService)


def test_factory_returns_openai_service_when_provider_is_openai(monkeypatch):
    from app.llm.factory import get_llm_service
    from app.llm.services.openai_service import OpenAIService

    monkeypatch.setenv("LLM_PROVIDER", "openai")

    assert isinstance(get_llm_service(), OpenAIService)


def test_factory_returns_claude_service_when_provider_is_claude(monkeypatch):
    from app.llm.factory import get_llm_service
    from app.llm.services.claude_service import ClaudeService

    monkeypatch.setenv("LLM_PROVIDER", "claude")

    assert isinstance(get_llm_service(), ClaudeService)


def test_factory_rejects_unsupported_provider(monkeypatch):
    from app.llm.errors import LLMConfigurationError
    from app.llm.factory import get_llm_service

    monkeypatch.setenv("LLM_PROVIDER", "unsupported")

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM provider: unsupported"):
        get_llm_service()

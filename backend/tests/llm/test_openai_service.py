import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_openai_service_requires_api_key(monkeypatch):
    from app.llm.errors import LLMConfigurationError
    from app.llm.services.openai_service import OpenAIService

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY is missing."):
        OpenAIService().generate("prompt", "test-model")


def test_openai_service_calls_responses_api_with_prompt_and_model(monkeypatch):
    from app.llm.services import openai_service
    from app.llm.services.openai_service import OpenAIService

    calls = []

    class FakeResponses:
        @staticmethod
        def create(model, input):
            calls.append((model, input))
            return type("FakeResponse", (), {"output_text": "generated care plan"})()

    class FakeOpenAI:
        def __init__(self, api_key):
            calls.append(("api_key", api_key))
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_service, "OpenAI", FakeOpenAI)

    content = OpenAIService().generate("built prompt", "test-model")

    assert content == "generated care plan"
    assert calls == [
        ("api_key", "test-key"),
        ("test-model", "built prompt"),
    ]


def test_openai_service_wraps_provider_failure(monkeypatch):
    from app.llm.errors import LLMProviderError
    from app.llm.services import openai_service
    from app.llm.services.openai_service import OpenAIService

    class FakeResponses:
        @staticmethod
        def create(model, input):
            raise RuntimeError("provider-secret-detail")

    class FakeOpenAI:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_service, "OpenAI", FakeOpenAI)

    with pytest.raises(LLMProviderError, match="OpenAI generation failed."):
        OpenAIService().generate("built prompt", "test-model")

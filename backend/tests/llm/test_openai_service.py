import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_openai_service_requires_api_key(monkeypatch):
    from app.llm.services.openai_service import OpenAIService

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        OpenAIService().generate("prompt", "test-model")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENAI_API_KEY is missing."


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

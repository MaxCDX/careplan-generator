import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_claude_service_requires_api_key(monkeypatch):
    from app.llm.services.claude_service import ClaudeService

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is not configured."):
        ClaudeService().generate("prompt", "claude-test-model")


def test_claude_service_calls_messages_api_with_prompt_and_model(monkeypatch):
    from app.llm.services import claude_service
    from app.llm.services.claude_service import ClaudeService

    calls = []

    class FakeMessages:
        @staticmethod
        def create(model, max_tokens, messages):
            calls.append(
                {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                }
            )
            content_block = type("FakeContentBlock", (), {"text": "generated care plan"})()
            return type("FakeMessage", (), {"content": [content_block]})()

    class FakeAnthropic:
        def __init__(self, api_key):
            calls.append({"api_key": api_key})
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setattr(claude_service, "Anthropic", FakeAnthropic)

    content = ClaudeService().generate("built prompt", "claude-test-model")

    assert content == "generated care plan"
    assert calls == [
        {"api_key": "test-anthropic-key"},
        {
            "model": "claude-test-model",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": "built prompt"}],
        },
    ]

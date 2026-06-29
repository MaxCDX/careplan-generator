import os

from app.llm.base import BaseLLMService
from app.llm.errors import LLMConfigurationError, LLMProviderError

Anthropic = None


def get_anthropic_client_class():
    """Return Anthropic client class, allowing tests to monkeypatch it."""
    if Anthropic is not None:
        return Anthropic

    from anthropic import Anthropic as AnthropicClient

    return AnthropicClient


class ClaudeService(BaseLLMService):
    """Claude-backed LLM service."""

    def generate(self, prompt: str, model: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMConfigurationError("ANTHROPIC_API_KEY is not configured.")

        try:
            client_class = get_anthropic_client_class()
            client = client_class(api_key=api_key)
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMProviderError("Claude generation failed.") from exc

        return message.content[0].text

import os

from app.llm.base import BaseLLMService
from app.llm.errors import LLMConfigurationError
from app.llm.services.claude_service import ClaudeService
from app.llm.services.mock_service import MockLLMService
from app.llm.services.openai_service import OpenAIService


def get_llm_service() -> BaseLLMService:
    """Return the configured LLM provider service."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    if provider == "mock":
        return MockLLMService()

    if provider == "openai":
        return OpenAIService()

    if provider == "claude":
        return ClaudeService()

    raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")

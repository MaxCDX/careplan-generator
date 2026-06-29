import os

from openai import OpenAI

from app.llm.base import BaseLLMService
from app.llm.errors import LLMConfigurationError, LLMProviderError


class OpenAIService(BaseLLMService):
    """OpenAI-backed LLM service."""

    def generate(self, prompt: str, model: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is missing.")

        try:
            client = OpenAI(api_key=api_key)
            response = client.responses.create(model=model, input=prompt)
        except Exception as exc:
            raise LLMProviderError("OpenAI generation failed.") from exc

        return response.output_text

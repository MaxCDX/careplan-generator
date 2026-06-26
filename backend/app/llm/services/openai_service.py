import os

from fastapi import HTTPException
from openai import OpenAI

from app.llm.base import BaseLLMService


class OpenAIService(BaseLLMService):
    """OpenAI-backed LLM service."""

    def generate(self, prompt: str, model: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

        client = OpenAI(api_key=api_key)
        response = client.responses.create(model=model, input=prompt)
        return response.output_text

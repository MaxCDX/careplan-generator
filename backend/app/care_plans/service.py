"""Care plan generation business logic."""

import os
import time

from fastapi import HTTPException
from openai import OpenAI

from app.care_plans.prompts import build_prompt

MOCK_CARE_PLAN_CONTENT = """Problem list:
- Mock problem list for local care plan testing.

Goals:
- Mock goal for local care plan testing.

Pharmacist interventions:
- Mock pharmacist intervention for local care plan testing.

Monitoring plan:
- Mock monitoring plan for local care plan testing."""


def get_llm_provider() -> str:
    """Return the configured LLM provider, defaulting to real OpenAI."""
    return os.getenv("LLM_PROVIDER", "openai").lower()


def get_mock_llm_delay_secs() -> float:
    """Return optional mock LLM delay for local Celery-flow testing."""
    return float(os.getenv("MOCK_LLM_DELAY_SECS", "0"))


def generate_mock_care_plan_content() -> str:
    """Return deterministic mock care plan content for local development."""
    delay_secs = get_mock_llm_delay_secs()
    if delay_secs > 0:
        time.sleep(delay_secs)
    return MOCK_CARE_PLAN_CONTENT


def generate_care_plan_content(order, model: str) -> str:
    """Return generated care plan text using the configured LLM provider."""
    if get_llm_provider() == "mock":
        return generate_mock_care_plan_content()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=model, input=build_prompt(order))
    return response.output_text

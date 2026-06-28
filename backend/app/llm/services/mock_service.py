import os
import time

from app.llm.base import BaseLLMService
from app.llm.errors import LLMConfigurationError

MOCK_CARE_PLAN_CONTENT = """Problem list:
- Mock problem list for local care plan testing.

Goals:
- Mock goal for local care plan testing.

Pharmacist interventions:
- Mock pharmacist intervention for local care plan testing.

Monitoring plan:
- Mock monitoring plan for local care plan testing."""


def get_mock_llm_delay_secs() -> float:
    """Return optional mock LLM delay for local Celery-flow testing."""
    try:
        return float(os.getenv("MOCK_LLM_DELAY_SECS", "0"))
    except ValueError as exc:
        raise LLMConfigurationError("MOCK_LLM_DELAY_SECS must be a number.") from exc


class MockLLMService(BaseLLMService):
    """Deterministic LLM service for local development and tests."""

    def generate(self, prompt: str, model: str) -> str:
        delay_secs = get_mock_llm_delay_secs()
        if delay_secs > 0:
            time.sleep(delay_secs)
        return MOCK_CARE_PLAN_CONTENT

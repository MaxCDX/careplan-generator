"""Care plan generation business logic."""

from app.care_plans.prompts import build_prompt
from app.llm.factory import get_llm_service


def generate_care_plan_content(order, model: str) -> str:
    """Return generated care plan text using the configured LLM provider."""
    prompt = build_prompt(order)
    llm_service = get_llm_service()
    return llm_service.generate(prompt, model)

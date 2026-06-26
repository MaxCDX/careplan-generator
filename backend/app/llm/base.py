class BaseLLMService:
    """Minimal interface for LLM text generation providers."""

    def generate(self, prompt: str, model: str) -> str:
        raise NotImplementedError

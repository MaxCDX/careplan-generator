class LLMConfigurationError(RuntimeError):
    """Raised when an LLM provider is not configured correctly."""


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider request fails."""

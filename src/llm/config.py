"""LLM configuration classes."""

from dataclasses import dataclass, field
from enum import StrEnum


class LLMBackendType(StrEnum):
    """Supported LLM backend types."""
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible" 
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


@dataclass
class LLMConfig:
    """Configuration for LLM backends."""
    backend: LLMBackendType = LLMBackendType.OLLAMA
    endpoint: str = "http://localhost:11434"
    model: str | None = None  # None = auto-detect from inference endpoint
    timeout_seconds: float = 120.0
    api_key: str | None = None
    fallback_models: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "LLMConfig":
        """Create config from dictionary."""
        # Extract LLM-specific config if nested
        llm_data = data.get("llm", data)
        
        return cls(
            backend=LLMBackendType(llm_data.get("backend", "ollama")),
            endpoint=llm_data.get("endpoint", "http://localhost:11434"),
            model=llm_data.get("model"),
            timeout_seconds=llm_data.get("timeout_seconds", 120.0),
            api_key=llm_data.get("api_key"),
            fallback_models=llm_data.get("fallback_models", []),
        )
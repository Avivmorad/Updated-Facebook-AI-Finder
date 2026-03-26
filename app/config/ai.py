import os
from dataclasses import dataclass, field


def _env_text(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AIConfig:
    provider: str = field(default_factory=lambda: _env_text("AI_PROVIDER", "groq").lower())
    groq_model_name: str = field(default_factory=lambda: _env_text("GROQ_MODEL_NAME", "llama-3.1-8b-instant"))
    gemini_model_name: str = field(default_factory=lambda: _env_text("GEMINI_MODEL_NAME", "gemini-1.5-flash"))
    timeout_seconds: int = field(default_factory=lambda: _env_int("AI_TIMEOUT_SECONDS", 20))
    retry_attempts: int = field(
        default_factory=lambda: _env_int("AI_RETRY_ATTEMPTS", 2)
    )
    retry_backoff_seconds: float = field(default_factory=lambda: _env_float("AI_RETRY_BACKOFF_SECONDS", 0.4))
    max_output_tokens: int = field(default_factory=lambda: _env_int("AI_MAX_OUTPUT_TOKENS", 700))
    temperature: float = field(default_factory=lambda: _env_float("AI_TEMPERATURE", 0.2))


AIAnalysisConfig = AIConfig

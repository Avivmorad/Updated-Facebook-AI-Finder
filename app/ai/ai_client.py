import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Protocol

from app.models.ai_models import AIPromptPacket
from config.ai_analysis_config import AIAnalysisConfig

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional bootstrap helper
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


@dataclass
class AIClientResult:
    raw_text: str
    raw_data: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AIClientProtocol(Protocol):
    def generate(self, prompt: AIPromptPacket) -> AIClientResult:
        ...


class GroqClient:
    def __init__(self, config: Optional[AIAnalysisConfig] = None) -> None:
        self._config = config or AIAnalysisConfig()
        self._api_key = os.getenv("GROQ_API_KEY", "").strip()

    def generate(self, prompt: AIPromptPacket) -> AIClientResult:
        if not self._api_key:
            return AIClientResult(
                raw_text="",
                raw_data={},
                error="GROQ_API_KEY is not configured",
            )

        try:
            from openai import OpenAI
        except ImportError:
            return AIClientResult(raw_text="", raw_data={}, error="openai package is not available")

        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=self._config.timeout_seconds,
            )
            response = client.chat.completions.create(
                model=self._config.groq_model_name,
                temperature=self._config.temperature,
                max_tokens=self._config.max_output_tokens,
                messages=[
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_prompt},
                ],
            )

            content = ""
            if response.choices and response.choices[0].message is not None:
                content = response.choices[0].message.content or ""

            return AIClientResult(
                raw_text=content,
                raw_data=response.model_dump() if hasattr(response, "model_dump") else {},
            )
        except Exception as exc:  # noqa: BLE001
            return AIClientResult(raw_text="", raw_data={}, error=f"groq_request_failed: {str(exc)}")


class GeminiClient:
    def __init__(self, config: Optional[AIAnalysisConfig] = None) -> None:
        self._config = config or AIAnalysisConfig()
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate(self, prompt: AIPromptPacket) -> AIClientResult:
        if not self._api_key:
            return AIClientResult(
                raw_text="",
                raw_data={},
                error="GEMINI_API_KEY is not configured",
            )

        try:
            import google.generativeai as genai
        except ImportError:
            return AIClientResult(raw_text="", raw_data={}, error="google-generativeai package is not available")

        try:
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._config.gemini_model_name)
            response = model.generate_content(
                [prompt.system_prompt, prompt.user_prompt],
                generation_config={
                    "temperature": self._config.temperature,
                    "max_output_tokens": self._config.max_output_tokens,
                },
            )
            text = getattr(response, "text", "") or ""
            return AIClientResult(raw_text=text, raw_data=response.to_dict() if hasattr(response, "to_dict") else {})
        except Exception as exc:  # noqa: BLE001
            return AIClientResult(raw_text="", raw_data={}, error=f"gemini_request_failed: {str(exc)}")


def build_default_ai_client(config: Optional[AIAnalysisConfig] = None) -> AIClientProtocol:
    resolved = config or AIAnalysisConfig()
    provider = resolved.provider.strip().lower()

    if provider == "groq":
        return GroqClient(resolved)
    if provider == "gemini":
        return GeminiClient(resolved)

    return GroqClient(resolved)

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.config.ai import AIConfig
from app.config.browser import BrowserConfig


_ALLOWED_AI_PROVIDERS = {"groq", "gemini"}


@dataclass
class ValidationOutcome:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def merge(self, other: "ValidationOutcome") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def validate_ai_config(
    config: Optional[AIConfig] = None,
    require_api_key: bool = True,
) -> ValidationOutcome:
    cfg = config or AIConfig()
    outcome = ValidationOutcome()

    provider = (cfg.provider or "").strip().lower()
    if provider not in _ALLOWED_AI_PROVIDERS:
        outcome.errors.append("AI_PROVIDER must be one of: groq, gemini")
        return outcome

    key_env_name = "GROQ_API_KEY" if provider == "groq" else "GEMINI_API_KEY"
    key_value = os.getenv(key_env_name, "").strip()
    if not key_value:
        message = f"{key_env_name} is required when AI_PROVIDER={provider}"
        if require_api_key:
            outcome.errors.append(message)
        else:
            outcome.warnings.append(message + " (AI requests will fail until configured)")

    if cfg.retry_attempts < 0:
        outcome.errors.append("AI_RETRY_ATTEMPTS must be >= 0")

    if cfg.timeout_seconds <= 0:
        outcome.errors.append("AI_TIMEOUT_SECONDS must be > 0")

    return outcome


def validate_browser_config(
    config: Optional[BrowserConfig] = None,
    require_profile: bool = True,
) -> ValidationOutcome:
    cfg = config or BrowserConfig()
    outcome = ValidationOutcome()

    if not require_profile:
        return outcome

    user_data_raw = (cfg.chrome_user_data_dir or "").strip()
    if not user_data_raw:
        outcome.errors.append("CHROME_USER_DATA_DIR is required")
        return outcome

    normalized = user_data_raw.replace("\\", "/").strip().lower().rstrip("/")
    if normalized.endswith("/google/chrome/user data"):
        outcome.errors.append(
            "CHROME_USER_DATA_DIR cannot be the default Chrome User Data root; "
            "use a dedicated copied profile root"
        )

    user_data_dir = Path(user_data_raw).expanduser()
    if not user_data_dir.exists():
        outcome.errors.append(f"CHROME_USER_DATA_DIR does not exist: {user_data_dir}")
        return outcome

    profile_name = (cfg.chrome_profile_directory or "").strip()
    if not profile_name:
        outcome.errors.append("CHROME_PROFILE_DIRECTORY is required")
        return outcome

    profile_path = user_data_dir / profile_name
    if not profile_path.exists():
        outcome.errors.append(
            "CHROME_PROFILE_DIRECTORY was not found inside CHROME_USER_DATA_DIR: "
            f"{profile_path}"
        )

    if (user_data_dir / "SingletonLock").exists() or (user_data_dir / "lockfile").exists():
        outcome.warnings.append(
            "Chrome profile appears locked. Close all Chrome windows before running scraper"
        )

    return outcome


def validate_startup_config(
    require_api_key: bool = True,
    require_browser_profile: bool = True,
) -> List[str]:
    outcome = ValidationOutcome()
    outcome.merge(validate_ai_config(require_api_key=require_api_key))
    outcome.merge(validate_browser_config(require_profile=require_browser_profile))

    if outcome.errors:
        bullet_list = "\n".join([f"- {item}" for item in outcome.errors])
        raise ValueError(f"Startup configuration validation failed:\n{bullet_list}")

    return outcome.warnings

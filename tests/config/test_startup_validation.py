import pytest

from app.config.startup_validation import (
    validate_ai_config,
    validate_browser_config,
    validate_startup_config,
)


def test_validate_ai_config_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "unknown")
    result = validate_ai_config(require_api_key=True)
    assert any("AI_PROVIDER" in item for item in result.errors)


def test_validate_ai_config_requires_key_for_selected_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_VISION_MODEL_NAME", "llama-3.2-90b-vision-preview")
    result = validate_ai_config(require_api_key=True)
    assert any("GROQ_API_KEY" in item for item in result.errors)


def test_validate_ai_config_requires_groq_vision_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key")
    monkeypatch.delenv("GROQ_VISION_MODEL_NAME", raising=False)
    result = validate_ai_config(require_api_key=True)
    assert any("GROQ_VISION_MODEL_NAME" in item for item in result.errors)


def test_validate_browser_config_rejects_default_chrome_root(monkeypatch, tmp_path):
    chrome_root = tmp_path / "Google" / "Chrome" / "User Data"
    profile_dir = chrome_root / "Default"
    profile_dir.mkdir(parents=True)

    monkeypatch.setenv("CHROME_USER_DATA_DIR", str(chrome_root))
    monkeypatch.setenv("CHROME_PROFILE_DIRECTORY", "Default")

    result = validate_browser_config(require_profile=True)
    assert any(
        "cannot be the default Chrome User Data root" in item for item in result.errors
    )


def test_validate_startup_config_passes_for_valid_setup(monkeypatch, tmp_path):
    copied_root = tmp_path / "chrome_user_data"
    (copied_root / "Default").mkdir(parents=True)

    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key")
    monkeypatch.setenv("GROQ_VISION_MODEL_NAME", "llama-3.2-90b-vision-preview")
    monkeypatch.setenv("CHROME_USER_DATA_DIR", str(copied_root))
    monkeypatch.setenv("CHROME_PROFILE_DIRECTORY", "Default")

    warnings = validate_startup_config(
        require_api_key=True, require_browser_profile=True
    )
    assert isinstance(warnings, list)


def test_validate_startup_config_raises_for_missing_profile(monkeypatch, tmp_path):
    copied_root = tmp_path / "chrome_user_data"
    copied_root.mkdir(parents=True)

    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key")
    monkeypatch.setenv("GROQ_VISION_MODEL_NAME", "llama-3.2-90b-vision-preview")
    monkeypatch.setenv("CHROME_USER_DATA_DIR", str(copied_root))
    monkeypatch.setenv("CHROME_PROFILE_DIRECTORY", "Default")

    with pytest.raises(ValueError):
        validate_startup_config(require_api_key=True, require_browser_profile=True)

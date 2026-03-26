from pathlib import Path

import pytest

from app.browser.browser_session_manager import BrowserSessionManager
from app.config.browser import BrowserConfig
from app.utils.app_errors import AppError


def test_missing_user_data_dir_returns_specific_error():
    manager = BrowserSessionManager(BrowserConfig(chrome_user_data_dir="", chrome_profile_directory="Default"))
    with pytest.raises(AppError) as exc:
        manager._require_user_data_dir()
    assert exc.value.code == "ERR_BROWSER_USER_DATA_DIR_MISSING"


def test_missing_profile_dir_returns_specific_error(tmp_path):
    manager = BrowserSessionManager(
        BrowserConfig(
            chrome_user_data_dir=str(tmp_path),
            chrome_profile_directory="Profile 99",
        )
    )
    with pytest.raises(AppError) as exc:
        manager._require_profile_directory(Path(tmp_path))
    assert exc.value.code == "ERR_BROWSER_PROFILE_DIR_MISSING"


def test_locked_profile_returns_specific_error(tmp_path):
    (tmp_path / "Default").mkdir(parents=True, exist_ok=True)
    (tmp_path / "SingletonLock").write_text("lock", encoding="utf-8")
    manager = BrowserSessionManager(
        BrowserConfig(
            chrome_user_data_dir=str(tmp_path),
            chrome_profile_directory="Default",
        )
    )
    with pytest.raises(AppError) as exc:
        manager._check_profile_not_locked(Path(tmp_path))
    assert exc.value.code == "ERR_BROWSER_PROFILE_LOCKED"

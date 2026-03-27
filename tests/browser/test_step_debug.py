from pathlib import Path

from app.browser.step_debug import capture_browser_step, load_step_events, reset_step_debug_workspace
from app.config.browser import BrowserConfig


class _FakePage:
    url = "https://www.facebook.com/groups/feed/"

    def screenshot(self, *, path: str, full_page: bool = False):  # noqa: ARG002
        Path(path).write_bytes(b"fake-image")


def test_capture_browser_step_writes_image_and_event(tmp_path):
    config = BrowserConfig(
        step_debug_enabled=True,
        step_debug_dir=str(tmp_path / "browser_steps"),
    )
    reset_step_debug_workspace(config)

    image_path = capture_browser_step(
        config,
        page=_FakePage(),
        step_code="FACEBOOK_HOME_OPENED",
        message="Facebook home page opened",
        context="facebook_access",
    )

    assert image_path
    assert Path(image_path).exists() is True

    payload = load_step_events(config, limit=10)
    assert len(payload["events"]) == 1
    assert payload["events"][0]["step_code"] == "FACEBOOK_HOME_OPENED"


def test_capture_browser_step_returns_empty_when_disabled(tmp_path):
    config = BrowserConfig(
        step_debug_enabled=False,
        step_debug_dir=str(tmp_path / "browser_steps"),
    )
    reset_step_debug_workspace(config)
    image_path = capture_browser_step(
        config,
        page=_FakePage(),
        step_code="ANY",
        message="ignored",
    )
    assert image_path == ""


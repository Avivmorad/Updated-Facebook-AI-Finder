import os

from app.entrypoints.cli import _enforce_headless_by_debug_mode


def test_cli_enforces_headless_true_when_debugging_off_when_headless_is_unset(monkeypatch):
    monkeypatch.delenv("HEADLESS", raising=False)
    _enforce_headless_by_debug_mode(False)
    assert os.environ["HEADLESS"] == "true"


def test_cli_enforces_headless_false_when_debugging_on_when_headless_is_unset(monkeypatch):
    monkeypatch.delenv("HEADLESS", raising=False)
    _enforce_headless_by_debug_mode(True)
    assert os.environ["HEADLESS"] == "false"


def test_cli_keeps_explicit_headless_value(monkeypatch):
    monkeypatch.setenv("HEADLESS", "false")

    _enforce_headless_by_debug_mode(False)

    assert os.environ["HEADLESS"] == "false"

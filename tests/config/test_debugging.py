from app.utils.debugging import configure_debugging, is_debugging_enabled


def test_is_debugging_enabled_reads_env(monkeypatch):
    configure_debugging(None)
    monkeypatch.setenv("DEBUGGING", "true")
    assert is_debugging_enabled() is True
    configure_debugging(None)


def test_configure_debugging_overrides_env(monkeypatch):
    monkeypatch.setenv("DEBUGGING", "false")
    configure_debugging(True)
    assert is_debugging_enabled() is True
    configure_debugging(None)

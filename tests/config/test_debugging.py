from pathlib import Path

from app.utils.debugging import (
    close_debugging,
    configure_debugging,
    debug_step,
    get_debug_trace_file_path,
    is_debugging_enabled,
)


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


def test_debug_trace_file_created_and_written(tmp_path, capsys):
    trace_path = tmp_path / "debug_trace.txt"
    configure_debugging(True, str(trace_path))
    assert get_debug_trace_file_path() == str(trace_path)
    debug_step("DBG_TEST_TRACE", "writes a debug line")
    close_debugging()

    terminal_output = capsys.readouterr().out
    assert "DBG_TEST_TRACE" in terminal_output
    assert trace_path.exists() is True
    assert "DBG_TEST_TRACE" in trace_path.read_text(encoding="utf-8")

    configure_debugging(None)


def test_debug_trace_file_overwritten_between_runs(tmp_path):
    trace_path = tmp_path / "debug_trace.txt"
    configure_debugging(True, str(trace_path))
    debug_step("DBG_RUN_A", "line from first run")
    close_debugging()

    first_text = trace_path.read_text(encoding="utf-8")
    assert "DBG_RUN_A" in first_text

    configure_debugging(True, str(trace_path))
    debug_step("DBG_RUN_B", "line from second run")
    close_debugging()

    second_text = trace_path.read_text(encoding="utf-8")
    assert "DBG_RUN_B" in second_text
    assert "DBG_RUN_A" not in second_text

    configure_debugging(None)


def test_debug_trace_not_created_when_debugging_false(tmp_path):
    trace_path = Path(tmp_path) / "debug_trace.txt"
    configure_debugging(False, str(trace_path))
    debug_step("DBG_DISABLED", "should not be written")
    close_debugging()

    assert trace_path.exists() is False
    configure_debugging(None)


def test_debug_step_does_not_crash_when_stdout_unavailable(monkeypatch):
    configure_debugging(True)

    def _raise_oserror(*_args, **_kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr("builtins.print", _raise_oserror)
    debug_step("DBG_STDOUT_FAIL", "stdout unavailable should not crash")
    close_debugging()
    configure_debugging(None)

from pathlib import Path

from app.ui.run_manager import ManagedRunState, PipelineRunManager


class _RunningProcess:
    terminated = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True


class _FakeThread:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def start(self):
        return None


def test_start_run_rejects_empty_query(tmp_path):
    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )

    ok, message, _status = manager.start_run(query="  ", max_posts=20)

    assert ok is False
    assert message == "query is required"


def test_start_run_rejects_when_running(tmp_path):
    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )
    manager._state = ManagedRunState(  # type: ignore[attr-defined]
        status="running",
        run_id="run_test",
        query="iphone",
        max_posts=20,
    )
    manager._process = _RunningProcess()  # type: ignore[attr-defined]

    ok, message, status = manager.start_run(query="iphone", max_posts=20)

    assert ok is False
    assert message == "run already in progress"
    assert status["is_running"] is True


def test_stop_run_marks_state_as_stopping(tmp_path):
    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )
    process = _RunningProcess()
    manager._state = ManagedRunState(  # type: ignore[attr-defined]
        status="running",
        run_id="run_test",
        query="iphone",
        max_posts=20,
    )
    manager._process = process  # type: ignore[attr-defined]

    ok, message, status = manager.stop_run()

    assert ok is True
    assert message == "stop requested"
    assert process.terminated is True
    assert status["status"] == "stopping"
    assert status["can_stop"] is True


def test_finalize_locked_after_stop_marks_run_stopped(tmp_path):
    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )
    manager._state = ManagedRunState(  # type: ignore[attr-defined]
        status="stopping",
        run_id="run_test",
        query="iphone",
        max_posts=20,
        stop_reason="user_requested_stop",
    )
    manager._stop_requested = True  # type: ignore[attr-defined]

    manager._finalize_locked(exit_code=1)  # type: ignore[attr-defined]

    assert manager._state.status == "stopped"  # type: ignore[attr-defined]
    assert manager._state.error == ""  # type: ignore[attr-defined]


def test_start_run_can_show_browser_without_enabling_debugging(tmp_path, monkeypatch):
    captured = {}

    class _FakeProcess:
        def poll(self):
            return None

        def wait(self):
            return 0

        def terminate(self):
            return None

    def _fake_popen(command, cwd, env, stdout, stderr):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        return _FakeProcess()

    monkeypatch.setattr("app.ui.run_manager.subprocess.Popen", _fake_popen)
    monkeypatch.setattr("app.ui.run_manager.threading.Thread", _FakeThread)

    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )

    ok, message, status = manager.start_run(
        query="iphone",
        max_posts=5,
        tracking_enabled=False,
        debug_log_enabled=False,
        show_browser=True,
        slow_mo_ms=250,
    )

    assert ok is True
    assert message == "run started"
    assert "--debugging" not in captured["command"]
    assert captured["env"]["HEADLESS"] == "false"
    assert captured["env"]["FB_STEP_DEBUG_ENABLED"] == "false"
    assert captured["env"]["FB_SLOW_MO_MS"] == "250"
    assert status["show_browser"] is True
    assert status["tracking_enabled"] is False
    assert status["debug_log_enabled"] is False


def test_start_run_enables_debugging_for_tracking_mode(tmp_path, monkeypatch):
    captured = {}

    class _FakeProcess:
        def poll(self):
            return None

        def wait(self):
            return 0

        def terminate(self):
            return None

    def _fake_popen(command, cwd, env, stdout, stderr):
        captured["command"] = command
        captured["env"] = env
        return _FakeProcess()

    monkeypatch.setattr("app.ui.run_manager.subprocess.Popen", _fake_popen)
    monkeypatch.setattr("app.ui.run_manager.threading.Thread", _FakeThread)

    manager = PipelineRunManager(
        root_dir=Path(tmp_path),
        output_json_path=Path(tmp_path) / "data" / "reports" / "latest.json",
        trace_file_path=Path(tmp_path) / "data" / "logs" / "debug_trace.txt",
    )

    ok, _message, status = manager.start_run(
        query="iphone",
        max_posts=5,
        tracking_enabled=True,
        debug_log_enabled=False,
        show_browser=False,
        slow_mo_ms=250,
    )

    assert ok is True
    assert "--debugging" in captured["command"]
    assert captured["env"]["HEADLESS"] == "true"
    assert captured["env"]["FB_STEP_DEBUG_ENABLED"] == "true"
    assert captured["env"]["FB_SLOW_MO_MS"] == "250"
    assert status["tracking_enabled"] is True
    assert status["show_browser"] is False

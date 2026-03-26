import start


def test_start_main_does_not_emit_dbg_trace_file_line(monkeypatch, capsys):
    monkeypatch.setattr(start, "load_dotenv", lambda: None)
    monkeypatch.setattr(start, "_apply_runtime_env_overrides", lambda: None)
    monkeypatch.setattr(start, "_build_runtime_input", lambda: ({"query": "iphone 13"}, "query"))
    monkeypatch.setattr(start, "run_pipeline_from_input", lambda **_: 0)

    monkeypatch.setattr(start.settings, "DEBUGGING", True)
    monkeypatch.setattr(start.settings, "MAX_POSTS", 5)
    monkeypatch.setattr(start.settings, "CONTINUE_ON_POST_ERROR", True)
    monkeypatch.setattr(start.settings, "STOP_AFTER_POST_ERRORS", None)
    monkeypatch.setattr(start.settings, "SAVE_RUN_HISTORY", False)
    monkeypatch.setattr(start.settings, "OUTPUT_JSON", None)
    monkeypatch.setattr(start.settings, "DEBUG_TRACE_FILE", None)

    code = start.main()
    output = capsys.readouterr().out

    assert code == 0
    assert "DBG_TRACE_FILE" not in output
    assert "DBG_RUN_END" in output

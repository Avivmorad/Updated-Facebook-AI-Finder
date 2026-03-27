from pathlib import Path

from app.ui.debug_trace import parse_debug_line, read_trace_events


def test_parse_debug_line_extracts_fields():
    line = "[DEBUG 12:34:56] STEP DBG_STAGE_2_SEARCH | Stage 2/8: scanning groups feed."
    event = parse_debug_line(line)

    assert event is not None
    assert event.clock == "12:34:56"
    assert event.kind == "STEP"
    assert event.code == "DBG_STAGE_2_SEARCH"
    assert event.stage == "search"


def test_read_trace_events_filters_info_and_technical(tmp_path):
    trace_path = Path(tmp_path) / "debug_trace.txt"
    trace_path.write_text(
        "\n".join(
            [
                "[DEBUG 10:00:00] INFO DBG_QUERY_VALUE | Search query: \"iphone\"",
                "[DEBUG 10:00:01] INFO ERR_GROUPS_SCAN_FAILED | Technical details: fatal_error=ERR_GROUPS_SCAN_FAILED",
                "[DEBUG 10:00:02] ERROR ERR_GROUPS_SCAN_FAILED | Groups feed scan failed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = read_trace_events(trace_path, include_info=False, include_technical=False)
    events = payload["events"]

    assert len(events) == 1
    assert events[0]["kind"] == "ERROR"
    assert events[0]["code"] == "ERR_GROUPS_SCAN_FAILED"


def test_read_trace_events_uses_cursor_incrementally(tmp_path):
    trace_path = Path(tmp_path) / "debug_trace.txt"
    trace_path.write_text("[DEBUG 10:00:00] STEP DBG_PIPELINE_START | Starting a new pipeline run.\n", encoding="utf-8")

    first = read_trace_events(trace_path, cursor=0, include_info=True)
    assert len(first["events"]) == 1
    assert first["events"][0]["code"] == "DBG_PIPELINE_START"

    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write("[DEBUG 10:00:01] RESULT DBG_PIPELINE_DONE | Pipeline completed.\n")

    second = read_trace_events(trace_path, cursor=int(first["next_cursor"]), include_info=True)
    assert len(second["events"]) == 1
    assert second["events"][0]["code"] == "DBG_PIPELINE_DONE"


#!/usr/bin/env python3
"""Run all tests and print a readable pass/fail summary."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TEST_DESCRIPTIONS = {
    "test_parse_ai_response_accepts_spec_schema": "AI response JSON matches expected schema",
    "test_parse_ai_response_rejects_unexpected_field": "AI response rejects fields not in schema",
    "test_parse_ai_response_extracts_json_from_markdown_fence": "AI response extracted from markdown code fence",
    "test_ai_service_maps_invalid_json_to_specific_error_code": "Invalid AI JSON -> specific error code",
    "test_ai_service_maps_empty_response_to_specific_error_code": "Empty AI response -> specific error code",
    "test_ai_service_maps_request_error_to_specific_error_code": "AI request error -> mapped error code",
    "test_ai_service_maps_missing_vision_model_to_specific_error_code": "Missing vision model -> specific error",
    "test_ai_service_maps_decommissioned_vision_model_to_specific_error_code": "Decommissioned model -> specific error",
    "test_ai_service_returns_specific_error_when_screenshot_is_missing": "Missing screenshot -> specific error",
    "test_validate_startup_config_raises_for_missing_profile": "Missing Chrome profile -> error",
    "test_apply_feed_filters_raises_when_recent_posts_filter_missing": "Feed filter missing -> error",
    "test_apply_feed_filters_raises_when_recent_posts_not_verified": "Feed filter not verified -> error",
    "test_missing_user_data_dir_returns_specific_error": "Missing user data dir -> specific error",
    "test_missing_profile_dir_returns_specific_error": "Missing profile dir -> specific error",
    "test_locked_profile_returns_specific_error": "Locked profile -> specific error",
    "test_pipeline_runner_rejects_post_when_ai_marks_not_recent": "AI not recent -> post rejected",
    "test_runner_maps_time_filter_reasons_to_specific_error_codes": "Time filter reasons -> error codes",
    "test_time_filter_returns_missing_publish_date_reason": "Missing date -> specific reason code",
    "test_time_filter_returns_unparseable_publish_date_reason": "Unparseable date -> specific reason code",
    "test_time_filter_returns_older_than_24_hours_reason": "Old date -> specific reason code",
    "test_bad_history_payload_falls_back_to_empty": "Bad history payload -> empty fallback",
    "test_save_run_raises_on_non_serializable_payload": "Non-serializable payload -> error",
    "test_cli_enforces_headless_true_when_debugging_off_when_headless_is_unset": "CLI sets headless=true when debug is off",
    "test_cli_enforces_headless_false_when_debugging_on_when_headless_is_unset": "CLI sets headless=false when debug is on",
    "test_cli_keeps_explicit_headless_value": "CLI keeps explicit HEADLESS env value",
    "test_safe_console_print_falls_back_for_unicode": "CLI safe print handles Unicode fallback",
    "test_start_run_can_show_browser_without_enabling_debugging": "UI can show browser without enabling debug mode",
    "test_start_run_enables_debugging_for_tracking_mode": "UI enables debug mode for tracking",
}


def _safe_print(message: str = "") -> None:
    text = str(message)
    try:
        print(text)
        return
    except UnicodeEncodeError:
        pass

    newline_text = text + "\n"
    stream = sys.stdout
    encoding = str(getattr(stream, "encoding", "") or "utf-8")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(newline_text.encode(encoding, errors="replace"))
        buffer.flush()
        return
    stream.write(newline_text.encode("ascii", errors="backslashreplace").decode("ascii"))
    stream.flush()


def _describe_test(name: str) -> str:
    if name in TEST_DESCRIPTIONS:
        return TEST_DESCRIPTIONS[name]
    readable = name.replace("test_", "").replace("_", " ").strip()
    return readable[:1].upper() + readable[1:] if readable else ""


def main() -> int:
    import pytest

    class SummaryPlugin:
        def __init__(self) -> None:
            self.results: list[tuple[str, str, str]] = []
            self.total = 0
            self.passed = 0
            self.failed = 0
            self.skipped = 0

        def pytest_runtest_logreport(self, report) -> None:  # noqa: ANN001
            if report.when != "call" and not (report.when == "setup" and report.outcome == "error"):
                return
            self.total += 1
            name = report.nodeid.rsplit("::", 1)[-1] if "::" in report.nodeid else report.nodeid
            desc = _describe_test(name)

            if report.passed:
                self.passed += 1
                self.results.append((name, "PASS", desc))
            elif report.failed:
                self.failed += 1
                self.results.append((name, "FAIL", desc))
            elif report.skipped:
                self.skipped += 1
                self.results.append((name, "SKIP", desc))

        def pytest_sessionfinish(self, session, exitstatus) -> None:  # noqa: ANN001, ARG002
            name_width = max((len(item[0]) for item in self.results), default=40)
            desc_width = max((len(item[2]) for item in self.results), default=30)
            total_width = name_width + desc_width + 18

            _safe_print()
            _safe_print("=" * total_width)
            _safe_print("  TEST RESULTS SUMMARY")
            _safe_print("=" * total_width)

            for name, outcome, desc in self.results:
                icon = {"PASS": "+", "FAIL": "X", "SKIP": "-"}.get(outcome, "?")
                line = f"  [{icon}] {outcome:<5} {name:<{name_width}}  {desc}"
                _safe_print(line)

            _safe_print("-" * total_width)
            parts = [f"Total: {self.total}", f"Passed: {self.passed}"]
            if self.failed:
                parts.append(f"FAILED: {self.failed}")
            if self.skipped:
                parts.append(f"Skipped: {self.skipped}")
            _safe_print(f"  {' | '.join(parts)}")

            if self.failed:
                _safe_print("\n  FAILED TESTS:")
                for name, outcome, desc in self.results:
                    if outcome == "FAIL":
                        _safe_print(f"    X  {name}  -  {desc}")

            if self.failed == 0 and self.total > 0:
                _safe_print("\n  ALL TESTS PASSED")
            _safe_print("=" * total_width)

    plugin = SummaryPlugin()
    exit_code = pytest.main(
        [
            "-c",
            str(PROJECT_ROOT / "pytest.ini"),
            "--rootdir",
            str(PROJECT_ROOT),
            "-q",
            "--tb=short",
            "--no-header",
            "--disable-warnings",
        ],
        plugins=[plugin],
    )
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())

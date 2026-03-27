#!/usr/bin/env python3
"""
Check Project Health — full environment and configuration check.

Validates Python version, .env values, dependencies, Chrome profile, app imports,
critical files, settings, and test collection — WITHOUT running the actual pipeline.
Prints a clear pass/fail summary for every check.
"""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _ok(msg: str) -> None:
    print(f"  [+] OK    {msg}")


def _warn(msg: str) -> None:
    print(f"  [!] WARN  {msg}")


def _fail(msg: str) -> None:
    print(f"  [X] FAIL  {msg}")


# ---------------------------------------------------------------------------
# Individual checks — each returns (errors, warnings)
# ---------------------------------------------------------------------------


def check_python_version() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    if sys.version_info < (3, 10):
        errors.append(f"Python 3.10+ required, got {sys.version.split()[0]}")
    else:
        _ok(f"Python {sys.version.split()[0]}")
    return errors, []


def check_env_file() -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        _ok(".env file found")
    else:
        warnings.append(".env file missing — copy .env.example and fill in values")
    return [], warnings


def check_env_values() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if not provider:
        errors.append("AI_PROVIDER not set in .env")
    elif provider not in ("groq",):
        errors.append(f"AI_PROVIDER='{provider}' — only 'groq' is supported")
    else:
        _ok(f"AI_PROVIDER={provider}")

    if provider == "groq":
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            errors.append("GROQ_API_KEY is empty")
        else:
            _ok("GROQ_API_KEY is set")

        vision = os.getenv("GROQ_VISION_MODEL_NAME", "").strip()
        if not vision:
            errors.append("GROQ_VISION_MODEL_NAME is empty")
        else:
            _ok(f"GROQ_VISION_MODEL_NAME={vision}")

    chrome_dir = os.getenv("CHROME_USER_DATA_DIR", "").strip()
    if not chrome_dir:
        errors.append("CHROME_USER_DATA_DIR is empty")
    else:
        chrome_path = Path(chrome_dir).expanduser()
        if chrome_path.exists():
            _ok(f"CHROME_USER_DATA_DIR exists: {chrome_path}")
        else:
            errors.append(f"CHROME_USER_DATA_DIR does not exist: {chrome_path}")

        profile = os.getenv("CHROME_PROFILE_DIRECTORY", "").strip()
        if not profile:
            errors.append("CHROME_PROFILE_DIRECTORY is empty")
        elif chrome_path.exists():
            profile_path = chrome_path / profile
            if profile_path.exists():
                _ok(f"Chrome profile found: {profile_path}")
            else:
                errors.append(f"Chrome profile not found: {profile_path}")

            local_state = chrome_path / "Local State"
            if not local_state.exists():
                warnings.append(
                    "Chrome 'Local State' missing — session cookies may fail"
                )

            if (chrome_path / "SingletonLock").exists() or (
                chrome_path / "lockfile"
            ).exists():
                warnings.append(
                    "Chrome profile appears locked — close all Chrome windows first"
                )

    return errors, warnings


def check_core_imports() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    modules = [
        ("playwright.sync_api", "playwright"),
        ("dotenv", "python-dotenv"),
        ("openai", "openai"),
    ]
    for mod_name, pip_name in modules:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            errors.append(f"Cannot import '{mod_name}' — pip install {pip_name}")
    if not errors:
        _ok("Core dependencies importable (playwright, dotenv, openai)")
    return errors, []


def check_app_modules() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    app_modules = [
        "app.config.ai",
        "app.config.browser",
        "app.config.startup_validation",
        "app.domain.input",
        "app.domain.pipeline",
        "app.domain.ai",
        "app.domain.posts",
        "app.domain.ranking",
        "app.utils.debugging",
        "app.utils.app_errors",
        "app.ai.ai_client",
        "app.ai.ai_service",
        "app.ai.prompt_builder",
        "app.ai.response_parser",
        "app.ai.payload_builder",
        "app.browser.browser_session_manager",
        "app.browser.facebook_access_adapter",
        "app.browser.facebook_login_state_detector",
        "app.browser.groups_feed_scanner",
        "app.browser.step_debug",
        "app.extraction.post_extractor",
        "app.extraction.post_normalizer",
        "app.pipeline.query_service",
        "app.pipeline.runner",
        "app.pipeline.search_service",
        "app.pipeline.time_filter",
        "app.presentation.result_presenter",
        "app.presentation.run_history_store",
        "app.ranking.ranker",
        "app.ui.server",
        "app.ui.run_manager",
        "app.ui.debug_trace",
        "app.entrypoints.cli",
        "app.entrypoints.ui",
    ]
    for mod in app_modules:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Import failed: {mod} — {exc}")
    if not errors:
        _ok(f"All {len(app_modules)} app modules import successfully")
    else:
        ok_count = len(app_modules) - len(errors)
        _ok(f"{ok_count}/{len(app_modules)} app modules imported")
    return errors, []


def check_critical_files() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    critical = [
        "start.py",
        "settings.py",
        "app/__init__.py",
        "app/config/ai.py",
        "app/config/browser.py",
        "app/config/startup_validation.py",
        "app/pipeline/runner.py",
        "app/pipeline/search_service.py",
        "app/pipeline/time_filter.py",
        "app/ai/ai_service.py",
        "app/ai/prompt_builder.py",
        "app/browser/browser_session_manager.py",
        "app/browser/groups_feed_scanner.py",
        "app/extraction/post_extractor.py",
        "app/presentation/result_presenter.py",
        "app/ranking/ranker.py",
    ]
    for rel in critical:
        full = PROJECT_ROOT / rel
        if full.exists():
            if full.stat().st_size == 0:
                warnings.append(f"File is empty: {rel}")
        else:
            errors.append(f"Critical file missing: {rel}")
    if not errors:
        _ok(f"All {len(critical)} critical files present")
    return errors, warnings


def check_data_dirs_writable() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    dirs = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "logs",
        PROJECT_ROOT / "data" / "reports",
        PROJECT_ROOT / "data" / "tmp",
    ]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            marker = d / ".livegate_test"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Directory not writable: {d} — {exc}")
    if not errors:
        _ok("Data directories writable (data/, logs/, reports/, tmp/)")
    return errors, []


def check_startup_validation() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        from app.config.startup_validation import (
            validate_ai_config,
            validate_browser_config,
        )

        ai = validate_ai_config(require_api_key=True)
        br = validate_browser_config(require_profile=True)
        errors.extend(ai.errors)
        errors.extend(br.errors)
        warnings.extend(ai.warnings)
        warnings.extend(br.warnings)
        if not ai.errors and not br.errors:
            _ok("Startup validation passed")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Startup validation error: {exc}")
    return errors, warnings


def check_playwright_chrome() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            browser.close()
        _ok("Playwright Chrome channel available")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Playwright Chrome launch failed: {exc}")
    return errors, []


def check_settings_file() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    settings_path = PROJECT_ROOT / "settings.py"
    if not settings_path.exists():
        errors.append("settings.py missing")
        return errors, warnings
    try:
        import settings as s

        run_mode = getattr(s, "RUN_MODE", None)
        if run_mode not in ("query", "file", "interactive", "demo"):
            errors.append(
                f"settings.RUN_MODE='{run_mode}' — must be query/file/interactive/demo"
            )
        else:
            _ok(f"settings.RUN_MODE={run_mode}")

        if run_mode == "file":
            input_file = getattr(s, "INPUT_FILE", "")
            if input_file and not (PROJECT_ROOT / input_file).exists():
                warnings.append(f"settings.INPUT_FILE not found: {input_file}")
            elif input_file:
                _ok(f"settings.INPUT_FILE exists: {input_file}")

        max_posts = getattr(s, "MAX_POSTS", None)
        if max_posts is not None and (not isinstance(max_posts, int) or max_posts < 1):
            errors.append(
                f"settings.MAX_POSTS={max_posts} — must be a positive integer"
            )
        else:
            _ok(f"settings.MAX_POSTS={max_posts}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Failed to import settings.py: {exc}")
    return errors, warnings


def check_tests() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        import pytest

        ini_path = PROJECT_ROOT / "pytest.ini"
        args = [
            "--collect-only",
            "-q",
            "--rootdir",
            str(PROJECT_ROOT),
            "--disable-warnings",
        ]
        if ini_path.exists():
            args.extend(["-c", str(ini_path)])

        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            exit_code = pytest.main(args + ["--no-header"])
        if exit_code == 0:
            _ok("All tests collected successfully (no import/syntax errors)")
        elif exit_code == 4:
            warnings.append("No tests collected — test directory may be empty")
        else:
            errors.append(
                "Test collection failed — some tests have import or syntax errors"
            )
    except ImportError:
        warnings.append("pytest not installed — cannot validate tests")
    return errors, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    checks = [
        ("Python Version", check_python_version),
        (".env File", check_env_file),
        ("Environment Values", check_env_values),
        ("Core Dependencies", check_core_imports),
        ("App Module Imports", check_app_modules),
        ("Critical Files", check_critical_files),
        ("Data Directories", check_data_dirs_writable),
        ("Settings File", check_settings_file),
        ("Startup Validation", check_startup_validation),
        ("Playwright Chrome", check_playwright_chrome),
        ("Test Collection", check_tests),
    ]

    all_errors: List[str] = []
    all_warnings: List[str] = []

    print("=" * 60)
    print("  PROJECT HEALTH CHECK")
    print("=" * 60)

    for section_name, check_fn in checks:
        print(f"\n  [{section_name}]")
        errors, warnings = check_fn()
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        for e in errors:
            _fail(e)
        for w in warnings:
            _warn(w)

    print("\n" + "=" * 60)

    for w in all_warnings:
        _warn(w)

    if all_errors:
        print(
            f"\n  RESULT: FAIL — {len(all_errors)} error(s), {len(all_warnings)} warning(s)"
        )
        print("\n  Errors:")
        for e in all_errors:
            print(f"    X  {e}")
        print("=" * 60)
        return 1

    print(f"\n  RESULT: PASS — 0 errors, {len(all_warnings)} warning(s)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

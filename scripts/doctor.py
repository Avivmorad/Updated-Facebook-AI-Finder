#!/usr/bin/env python3
"""Project doctor: validate environment and runtime prerequisites."""

import argparse
import importlib
import sys
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.browser.facebook_access_adapter import FacebookAccessAdapter  # noqa: E402
from app.config.ai import AIConfig  # noqa: E402
from app.config.startup_validation import validate_ai_config, validate_browser_config  # noqa: E402


def _ok(message: str) -> None:
    print(f"[OK]   {message}")


def _warn(message: str) -> None:
    print(f"[WARN] {message}")


def _fail(message: str) -> None:
    print(f"[FAIL] {message}")


def _check_python_version() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if sys.version_info < (3, 10):
        errors.append("Python 3.10+ is required")
    else:
        _ok(f"Python version is {sys.version.split()[0]}")
    return errors, warnings


def _check_env_file() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    env_path = Path(".env")
    if env_path.exists():
        _ok(".env file found")
    else:
        warnings.append(".env file not found. Copy .env.example and configure values")
    return errors, warnings


def _check_dependencies() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    provider = AIConfig().provider.strip().lower()

    required_packages = ["playwright", "dotenv"]
    if provider == "groq":
        required_packages.append("openai")
    elif provider == "gemini":
        required_packages.append("google.generativeai")
    else:
        warnings.append(f"Unknown AI provider configured: {provider}")

    for package_name in required_packages:
        try:
            importlib.import_module(package_name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to import {package_name}: {exc}")

    if not errors:
        _ok("Core runtime dependencies import successfully")

    return errors, warnings


def _check_playwright_chrome() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Playwright import failed: {exc}")
        return errors, warnings

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            browser.close()
            _ok("Chrome browser channel is available to Playwright")
    except Exception as exc:  # noqa: BLE001
        errors.append(
            "Playwright could not launch Chrome channel. Install Chrome and run 'playwright install' if needed. "
            f"Details: {exc}"
        )

    return errors, warnings


def _check_paths_writable() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    for target in [Path("logs"), Path("data")]:
        try:
            target.mkdir(parents=True, exist_ok=True)
            marker = target / ".doctor_write_test"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            _ok(f"Directory is writable: {target}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Directory is not writable: {target}. {exc}")

    return errors, warnings


def _check_startup_validation(require_api_key: bool) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    ai_result = validate_ai_config(require_api_key=require_api_key)
    browser_result = validate_browser_config(require_profile=True)

    for item in ai_result.warnings + browser_result.warnings:
        warnings.append(item)

    for item in ai_result.errors + browser_result.errors:
        errors.append(item)

    return errors, warnings


def _check_facebook_session() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        adapter = FacebookAccessAdapter()
        with adapter.authenticated_session():
            _ok("Facebook session check passed (authenticated session available)")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Facebook session is not ready: {exc}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Facebook Groups Post Finder & Matcher environment and setup"
    )
    parser.add_argument(
        "--allow-missing-ai-key",
        action="store_true",
        help="Treat missing provider API key as warning instead of failure",
    )
    parser.add_argument(
        "--check-facebook-session",
        action="store_true",
        help="Try opening an authenticated Facebook session",
    )
    args = parser.parse_args()

    load_dotenv()

    all_errors: List[str] = []
    all_warnings: List[str] = []

    checks = [
        _check_python_version,
        _check_env_file,
        _check_dependencies,
        _check_playwright_chrome,
        _check_paths_writable,
    ]

    for check in checks:
        errors, warnings = check()
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    errors, warnings = _check_startup_validation(
        require_api_key=not args.allow_missing_ai_key
    )
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    if args.check_facebook_session:
        errors, warnings = _check_facebook_session()
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    for warning in all_warnings:
        _warn(warning)

    if all_errors:
        for error in all_errors:
            _fail(error)
        print(
            f"Doctor finished with {len(all_errors)} error(s) and {len(all_warnings)} warning(s)."
        )
        return 1

    print(f"Doctor finished successfully with {len(all_warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

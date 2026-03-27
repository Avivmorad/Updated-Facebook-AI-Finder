from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AppErrorTemplate:
    code: str
    summary_he: str
    cause_he: str
    action_he: str


ERROR_CATALOG: Dict[str, AppErrorTemplate] = {
    "ERR_INPUT_MODE_INVALID": AppErrorTemplate(
        code="ERR_INPUT_MODE_INVALID",
        summary_he="Invalid input mode selection",
        cause_he="Multiple input modes were selected or RUN_MODE is invalid",
        action_he="Select only one valid input mode and run again",
    ),
    "ERR_INPUT_QUERY_MISSING": AppErrorTemplate(
        code="ERR_INPUT_QUERY_MISSING",
        summary_he="The query field is missing or empty",
        cause_he="A valid query value was not provided",
        action_he="Provide a non-empty query in settings or input JSON",
    ),
    "ERR_INPUT_FILE_NOT_FOUND": AppErrorTemplate(
        code="ERR_INPUT_FILE_NOT_FOUND",
        summary_he="Input file was not found",
        cause_he="The configured INPUT_FILE path does not exist",
        action_he="Check INPUT_FILE path and run again",
    ),
    "ERR_INPUT_JSON_INVALID": AppErrorTemplate(
        code="ERR_INPUT_JSON_INVALID",
        summary_he="Input file is not valid JSON",
        cause_he="The file could not be parsed as a valid JSON object",
        action_he="Fix the input JSON format and run again",
    ),
    "ERR_STARTUP_CONFIG_INVALID": AppErrorTemplate(
        code="ERR_STARTUP_CONFIG_INVALID",
        summary_he="Startup configuration is invalid",
        cause_he="One or more required startup settings are missing or invalid",
        action_he="Fix startup settings in .env/settings and run again",
    ),
    "ERR_BROWSER_USER_DATA_DIR_MISSING": AppErrorTemplate(
        code="ERR_BROWSER_USER_DATA_DIR_MISSING",
        summary_he="Chrome user data directory is missing",
        cause_he="CHROME_USER_DATA_DIR is empty or points to a missing path",
        action_he="Set CHROME_USER_DATA_DIR correctly in .env",
    ),
    "ERR_BROWSER_PROFILE_DIR_MISSING": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_DIR_MISSING",
        summary_he="Chrome profile directory was not found",
        cause_he="CHROME_PROFILE_DIRECTORY was not found inside CHROME_USER_DATA_DIR",
        action_he="Set CHROME_PROFILE_DIRECTORY to the exact profile folder name",
    ),
    "ERR_BROWSER_PROFILE_LOCKED": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_LOCKED",
        summary_he="Chrome profile is locked by another process",
        cause_he="Chrome is still running and lock files are present",
        action_he="Close all Chrome windows and try again",
    ),
    "ERR_BROWSER_PROFILE_INCOMPATIBLE": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_INCOMPATIBLE",
        summary_he="Configured Chrome profile could not be opened",
        cause_he="Copied profile may be incompatible, incomplete, or corrupted",
        action_he="Recreate copied profile, sign in manually, then retry",
    ),
    "ERR_FACEBOOK_HOME_OPEN_FAILED": AppErrorTemplate(
        code="ERR_FACEBOOK_HOME_OPEN_FAILED",
        summary_he="Failed to open Facebook home page",
        cause_he="Navigation failed or returned a non-OK HTTP status",
        action_he="Check network and Chrome profile session, then retry",
    ),
    "ERR_FACEBOOK_NOT_LOGGED_IN": AppErrorTemplate(
        code="ERR_FACEBOOK_NOT_LOGGED_IN",
        summary_he="Facebook is not logged in for the selected profile",
        cause_he="A login or checkpoint state was detected",
        action_he="Open that profile manually, log in to Facebook, then retry",
    ),
    "ERR_GROUPS_FEED_OPEN_FAILED": AppErrorTemplate(
        code="ERR_GROUPS_FEED_OPEN_FAILED",
        summary_he="Failed to open Facebook Groups feed",
        cause_he="Navigation to groups feed failed or landed on invalid page",
        action_he="Check groups feed URL and account access to groups",
    ),
    "ERR_FILTER_RECENT_NOT_FOUND": AppErrorTemplate(
        code="ERR_FILTER_RECENT_NOT_FOUND",
        summary_he="Recent posts filter was not found",
        cause_he="Expected selectors or buttons were not found in current UI",
        action_he="Stop run and update filter selectors for the current Facebook UI",
    ),
    "ERR_FILTER_LAST24_NOT_FOUND": AppErrorTemplate(
        code="ERR_FILTER_LAST24_NOT_FOUND",
        summary_he="Last 24 hours filter was not found",
        cause_he="Expected filter control was missing or not clickable",
        action_he="Continue; hard 24-hour filter in code will still be applied",
    ),
    "ERR_GROUPS_SCAN_FAILED": AppErrorTemplate(
        code="ERR_GROUPS_SCAN_FAILED",
        summary_he="Groups feed scan failed",
        cause_he="All scan attempts failed",
        action_he="Check connection, profile state, and group access, then retry",
    ),
    "ERR_NO_POST_LINKS_FOUND": AppErrorTemplate(
        code="ERR_NO_POST_LINKS_FOUND",
        summary_he="No post links were found during scan",
        cause_he="No matching post cards were detected",
        action_he="Increase scroll rounds or rerun later",
    ),
    "ERR_POST_LINK_MISSING": AppErrorTemplate(
        code="ERR_POST_LINK_MISSING",
        summary_he="Post link is missing",
        cause_he="Candidate post object did not contain a valid post_link",
        action_he="Skip this item and inspect scan output mapping",
    ),
    "ERR_POST_PAGE_LOAD_FAILED": AppErrorTemplate(
        code="ERR_POST_PAGE_LOAD_FAILED",
        summary_he="Post page failed to load",
        cause_he="Navigation failed or returned a non-OK HTTP status",
        action_he="Retry; if repeated, verify post URL accessibility",
    ),
    "ERR_POST_TEXT_NOT_FOUND": AppErrorTemplate(
        code="ERR_POST_TEXT_NOT_FOUND",
        summary_he="Post text was not found",
        cause_he="No matching text element was found by selectors",
        action_he="Continue; AI can still analyze available signals",
    ),
    "ERR_POST_IMAGES_NOT_FOUND": AppErrorTemplate(
        code="ERR_POST_IMAGES_NOT_FOUND",
        summary_he="Post images were not found",
        cause_he="No image elements were found or post has no images",
        action_he="Continue; AI will analyze text only",
    ),
    "ERR_POST_SCREENSHOT_CAPTURE_FAILED": AppErrorTemplate(
        code="ERR_POST_SCREENSHOT_CAPTURE_FAILED",
        summary_he="Post screenshot capture failed",
        cause_he="Playwright could not capture a screenshot for this post",
        action_he="Retry; if repeated, check page load stability and write permissions",
    ),
    "ERR_POST_SCREENSHOT_MISSING": AppErrorTemplate(
        code="ERR_POST_SCREENSHOT_MISSING",
        summary_he="Post screenshot is missing",
        cause_he="No screenshot path was available for AI vision analysis",
        action_he="Skip this post and verify screenshot capture in extractor",
    ),
    "ERR_POST_PUBLISH_DATE_MISSING": AppErrorTemplate(
        code="ERR_POST_PUBLISH_DATE_MISSING",
        summary_he="Post publish date is missing",
        cause_he="No publish timestamp could be extracted from post page",
        action_he="Continue; AI will evaluate recency from screenshot and available hints",
    ),
    "ERR_POST_PUBLISH_DATE_UNPARSEABLE": AppErrorTemplate(
        code="ERR_POST_PUBLISH_DATE_UNPARSEABLE",
        summary_he="Publish date could not be parsed",
        cause_he="Extracted date format is not supported by parser",
        action_he="Skip this post or extend date parser for this format",
    ),
    "ERR_POST_TOO_OLD": AppErrorTemplate(
        code="ERR_POST_TOO_OLD",
        summary_he="Post was rejected because it is older than 24 hours",
        cause_he="Hard 24-hour filter marked this post as out of range",
        action_he="No action required; pipeline continues",
    ),
    "ERR_AI_REQUEST_FAILED": AppErrorTemplate(
        code="ERR_AI_REQUEST_FAILED",
        summary_he="AI request failed",
        cause_he="Provider returned an error or timed out",
        action_he="Retry and verify API key, provider, model, and network",
    ),
    "ERR_AI_VISION_MODEL_MISSING": AppErrorTemplate(
        code="ERR_AI_VISION_MODEL_MISSING",
        summary_he="Groq vision model is missing",
        cause_he="GROQ_VISION_MODEL_NAME was not configured for screenshot analysis",
        action_he="Set GROQ_VISION_MODEL_NAME in .env and retry",
    ),
    "ERR_AI_VISION_PROVIDER_UNSUPPORTED": AppErrorTemplate(
        code="ERR_AI_VISION_PROVIDER_UNSUPPORTED",
        summary_he="Configured AI provider does not support required vision mode",
        cause_he="Current provider integration cannot accept screenshot payload",
        action_he="Use AI_PROVIDER=groq with a valid GROQ_VISION_MODEL_NAME",
    ),
    "ERR_AI_VISION_MODEL_DECOMMISSIONED": AppErrorTemplate(
        code="ERR_AI_VISION_MODEL_DECOMMISSIONED",
        summary_he="Configured Groq vision model is decommissioned",
        cause_he="Groq rejected the model because it is no longer supported",
        action_he="Set GROQ_VISION_MODEL_NAME to an active Groq vision model and retry",
    ),
    "ERR_AI_RESPONSE_EMPTY": AppErrorTemplate(
        code="ERR_AI_RESPONSE_EMPTY",
        summary_he="AI returned an empty response",
        cause_he="Provider returned empty text instead of JSON",
        action_he="Retry and verify provider limits",
    ),
    "ERR_AI_RESPONSE_INVALID_JSON": AppErrorTemplate(
        code="ERR_AI_RESPONSE_INVALID_JSON",
        summary_he="AI returned invalid JSON",
        cause_he="Model returned free text instead of valid JSON",
        action_he="Retry; if persistent, adjust provider/model or payload size",
    ),
    "ERR_AI_RESPONSE_SCHEMA_INVALID": AppErrorTemplate(
        code="ERR_AI_RESPONSE_SCHEMA_INVALID",
        summary_he="AI response does not match required schema",
        cause_he="Missing required fields, unexpected fields, or wrong types",
        action_he="Retry; if persistent, tighten prompt/schema handling",
    ),
    "ERR_AI_MARKED_NOT_RELEVANT": AppErrorTemplate(
        code="ERR_AI_MARKED_NOT_RELEVANT",
        summary_he="AI marked post as not relevant",
        cause_he="is_relevant was false",
        action_he="No action required; pipeline continues to next post",
    ),
    "ERR_AI_MARKED_NOT_RECENT": AppErrorTemplate(
        code="ERR_AI_MARKED_NOT_RECENT",
        summary_he="AI marked post as older than 24 hours",
        cause_he="is_recent_24h was false in AI response",
        action_he="No action required; pipeline continues to next post",
    ),
    "ERR_RESULT_SAVE_FAILED": AppErrorTemplate(
        code="ERR_RESULT_SAVE_FAILED",
        summary_he="Failed to save result JSON",
        cause_he="File write failed or permissions denied",
        action_he="Check output path permissions and retry",
    ),
    "ERR_DEBUG_TRACE_SAVE_FAILED": AppErrorTemplate(
        code="ERR_DEBUG_TRACE_SAVE_FAILED",
        summary_he="Failed to save debug trace file",
        cause_he="Trace file write failed",
        action_he="Check trace path permissions; terminal output will continue",
    ),
    "ERR_RUN_HISTORY_SAVE_FAILED": AppErrorTemplate(
        code="ERR_RUN_HISTORY_SAVE_FAILED",
        summary_he="Failed to save run history",
        cause_he="Writing run history file failed",
        action_he="Check write permissions for data/run_history.json",
    ),
    "ERR_PIPELINE_UNEXPECTED": AppErrorTemplate(
        code="ERR_PIPELINE_UNEXPECTED",
        summary_he="Unexpected pipeline error occurred",
        cause_he="An internal exception was raised without explicit mapping",
        action_he="Check logs and debug trace, then retry",
    ),
}


@dataclass
class AppError(Exception):
    code: str
    summary_he: str
    cause_he: str
    action_he: str
    technical_details: str = ""

    def __str__(self) -> str:
        return f"{self.code}: {self.summary_he}"

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "summary_he": self.summary_he,
            "cause_he": self.cause_he,
            "action_he": self.action_he,
            "technical_details": self.technical_details,
        }


def make_app_error(
    code: str,
    summary_he: Optional[str] = None,
    cause_he: Optional[str] = None,
    action_he: Optional[str] = None,
    technical_details: str = "",
) -> AppError:
    template = ERROR_CATALOG.get(code)
    resolved_summary = (summary_he or (template.summary_he if template else "Unexpected process error")).strip()
    resolved_cause = (cause_he or (template.cause_he if template else "No detailed cause available")).strip()
    resolved_action = (action_he or (template.action_he if template else "Check logs and retry")).strip()
    return AppError(
        code=str(code).strip() or "ERR_UNKNOWN",
        summary_he=resolved_summary,
        cause_he=resolved_cause,
        action_he=resolved_action,
        technical_details=technical_details.strip(),
    )


def normalize_app_error(
    exc: Exception,
    *,
    default_code: str,
    default_summary_he: Optional[str] = None,
    default_cause_he: Optional[str] = None,
    default_action_he: Optional[str] = None,
) -> AppError:
    if isinstance(exc, AppError):
        return exc
    return make_app_error(
        code=default_code,
        summary_he=default_summary_he,
        cause_he=default_cause_he,
        action_he=default_action_he,
        technical_details=str(exc),
    )


def find_first_app_error(*errors: Exception) -> Optional[AppError]:
    for err in errors:
        if isinstance(err, AppError):
            return err
    return None


def render_app_error_text(error: AppError, *, include_technical_details: bool = True) -> str:
    lines = [
        f"{error.code} | {error.summary_he}",
        f"Cause: {error.cause_he}",
        f"Action: {error.action_he}",
    ]
    if include_technical_details and error.technical_details:
        lines.append(f"Technical details: {error.technical_details}")
    return "\n".join(lines)

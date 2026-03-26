import base64
import logging
from pathlib import Path
from time import sleep
from typing import Any, Dict, Optional

from app.ai.ai_client import AIClientProtocol, build_default_ai_client
from app.ai.payload_builder import build_ai_request_payload
from app.ai.prompt_builder import build_ai_prompt
from app.ai.response_parser import parse_ai_response
from app.config.ai import AIConfig
from app.domain.ai import AIAnalysisEnvelope
from app.domain.input import UserQuery
from app.utils.app_errors import AppError, make_app_error
from app.utils.debugging import debug_app_error, debug_found, debug_info, debug_step
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class AIAnalysisService:
    def __init__(
        self,
        ai_client: Optional[AIClientProtocol] = None,
        config: Optional[AIConfig] = None,
    ) -> None:
        self._config = config or AIConfig()
        self._ai_client = ai_client or build_default_ai_client(self._config)

    def analyze(self, post_data: Dict[str, Any], user_query: UserQuery) -> AIAnalysisEnvelope:
        payload = build_ai_request_payload(post_data=post_data, user_query=user_query)
        prompt = build_ai_prompt(payload)
        payload_dict = payload.to_dict()
        screenshot_data_url, screenshot_error = self._build_screenshot_data_url(payload.post_screenshot_path)
        if screenshot_error is not None:
            debug_app_error(screenshot_error, include_technical_details=False)
            return AIAnalysisEnvelope(
                result=None,
                raw_response_text="",
                raw_response_data={"request_payload": payload_dict},
                validation_errors=[screenshot_error.code],
                success=False,
            )

        debug_step(
            "DBG_AI_SEND",
            (
                f"Sending post to AI with {len(payload.image_urls)} image URL(s), "
                f"{len(payload.post_text)} text characters, and screenshot: {payload.post_screenshot_path}."
            ),
        )

        max_attempts = max(1, self._config.retry_attempts + 1)
        last_raw_text = ""
        last_raw_data: Dict[str, Any] = {}
        last_errors: list[str] = []

        for attempt in range(1, max_attempts + 1):
            debug_info("DBG_AI_ATTEMPT", f"AI attempt {attempt}/{max_attempts}.")
            client_result = self._ai_client.generate(prompt, screenshot_data_url=screenshot_data_url)
            last_raw_text = client_result.raw_text
            last_raw_data = dict(client_result.raw_data)

            if client_result.error:
                request_error = _build_request_app_error(client_result.error)
                last_errors = [request_error.code]
                log_event(
                    logger,
                    logging.WARNING,
                    "ai_client_error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=request_error.technical_details,
                )
                debug_app_error(request_error)
            else:
                parsed, validation_errors, parsed_obj = parse_ai_response(client_result.raw_text)
                if parsed is not None:
                    debug_found(
                        "DBG_AI_DONE",
                        (
                            "AI returned a valid response: "
                            f"relevant={parsed.is_relevant}, score={parsed.match_score}, "
                            f"recent_24h={parsed.is_recent_24h}, confidence={parsed.confidence}."
                        ),
                    )
                    return AIAnalysisEnvelope(
                        result=parsed,
                        raw_response_text=client_result.raw_text,
                        raw_response_data={
                            **client_result.raw_data,
                            "parsed_response": parsed_obj,
                            "request_payload": payload_dict,
                            "attempt": attempt,
                        },
                        validation_errors=[],
                        success=True,
                    )

                parse_error = _build_parse_app_error(validation_errors)
                last_errors = [parse_error.code]
                last_raw_data = {
                    **client_result.raw_data,
                    "parsed_response": parsed_obj,
                    "validation_errors": validation_errors,
                }
                log_event(
                    logger,
                    logging.WARNING,
                    "ai_parse_error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    errors=";".join(validation_errors),
                )
                debug_app_error(parse_error)

            if attempt < max_attempts:
                sleep(max(0.0, self._config.retry_backoff_seconds) * attempt)

        final_error = make_app_error(code=last_errors[0] if last_errors else "ERR_AI_REQUEST_FAILED")
        debug_app_error(final_error)
        return AIAnalysisEnvelope(
            result=None,
            raw_response_text=last_raw_text,
            raw_response_data={
                **last_raw_data,
                "request_payload": payload_dict,
            },
            validation_errors=last_errors,
            success=False,
        )

    def _build_screenshot_data_url(self, screenshot_path: str) -> tuple[str, Optional[AppError]]:
        path_text = str(screenshot_path or "").strip()
        if not path_text:
            return "", make_app_error(code="ERR_POST_SCREENSHOT_MISSING")

        path = Path(path_text).expanduser()
        if not path.exists():
            return "", make_app_error(
                code="ERR_POST_SCREENSHOT_MISSING",
                technical_details=f"path_not_found={path}",
            )

        try:
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            return "", make_app_error(
                code="ERR_POST_SCREENSHOT_CAPTURE_FAILED",
                technical_details=f"path={path} error={exc}",
            )

        return f"data:image/png;base64,{payload}", None


def _build_parse_app_error(validation_errors: list[str]) -> AppError:
    if any(item == "empty_ai_response" for item in validation_errors):
        return make_app_error(
            code="ERR_AI_RESPONSE_EMPTY",
            technical_details=";".join(validation_errors),
        )
    if any(item.startswith("invalid_json:") for item in validation_errors):
        return make_app_error(
            code="ERR_AI_RESPONSE_INVALID_JSON",
            technical_details=";".join(validation_errors),
        )
    return make_app_error(
        code="ERR_AI_RESPONSE_SCHEMA_INVALID",
        technical_details=";".join(validation_errors),
    )


def _build_request_app_error(error_text: str) -> AppError:
    cleaned = str(error_text or "").strip()
    if "groq_vision_model_missing" in cleaned:
        return make_app_error(
            code="ERR_AI_VISION_MODEL_MISSING",
            technical_details=cleaned,
        )
    if "model_decommissioned" in cleaned:
        return make_app_error(
            code="ERR_AI_VISION_MODEL_DECOMMISSIONED",
            technical_details=cleaned,
        )
    if "vision_provider_unsupported" in cleaned:
        return make_app_error(
            code="ERR_AI_VISION_PROVIDER_UNSUPPORTED",
            technical_details=cleaned,
        )
    return make_app_error(
        code="ERR_AI_REQUEST_FAILED",
        technical_details=cleaned,
    )

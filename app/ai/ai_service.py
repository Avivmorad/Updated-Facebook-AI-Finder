import logging
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
        debug_step(
            "DBG_AI_SEND",
            f"שולח ל-AI פוסט עם {len(payload.image_urls)} תמונות ו-{len(payload.post_text)} תווים של טקסט.",
        )

        max_attempts = max(1, self._config.retry_attempts + 1)
        last_raw_text = ""
        last_raw_data: Dict[str, Any] = {}
        last_errors: list[str] = []

        for attempt in range(1, max_attempts + 1):
            debug_info("DBG_AI_ATTEMPT", f"ניסיון AI {attempt}/{max_attempts}.")
            client_result = self._ai_client.generate(prompt)
            last_raw_text = client_result.raw_text
            last_raw_data = dict(client_result.raw_data)

            if client_result.error:
                request_error = make_app_error(
                    code="ERR_AI_REQUEST_FAILED",
                    technical_details=client_result.error,
                )
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
                            "ה-AI החזיר תשובה תקינה: "
                            f"relevant={parsed.is_relevant}, score={parsed.match_score}, confidence={parsed.confidence}."
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

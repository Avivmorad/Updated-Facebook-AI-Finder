import logging
from time import sleep
from typing import Any, Dict, Optional

from app.ai.ai_client import AIClientProtocol, build_default_ai_client
from app.ai.payload_builder import build_ai_request_payload
from app.ai.prompt_builder import build_ai_prompt
from app.ai.response_parser import parse_ai_response
from app.models.ai_models import AIAnalysisEnvelope, AIParsedAnalysis
from app.models.input_models import SearchRequest
from app.utils.logger import get_logger, log_event
from config.ai_analysis_config import AIAnalysisConfig


logger = get_logger(__name__)


class AIAnalysisService:
    def __init__(
        self,
        ai_client: Optional[AIClientProtocol] = None,
        config: Optional[AIAnalysisConfig] = None,
    ) -> None:
        self._config = config or AIAnalysisConfig()
        self._ai_client = ai_client or build_default_ai_client(self._config)

    def analyze(self, post_data: Dict[str, Any], request: SearchRequest) -> AIAnalysisEnvelope:
        payload = build_ai_request_payload(post_data=post_data, request=request)
        prompt = build_ai_prompt(payload)

        payload_dict = payload.to_dict()
        max_attempts = max(1, self._config.retry_attempts + 1)
        last_reason = "ai_request_failed"
        last_raw_text = ""
        last_raw_data: Dict[str, Any] = {}
        last_validation_errors: list[str] = []

        for attempt in range(1, max_attempts + 1):
            client_result = self._ai_client.generate(prompt)
            last_raw_text = client_result.raw_text
            last_raw_data = dict(client_result.raw_data)

            if client_result.error:
                last_reason = client_result.error
                log_event(
                    logger,
                    logging.WARNING,
                    "ai_client_error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    reason=client_result.error,
                )
            else:
                parsed, validation_errors, parsed_obj = parse_ai_response(client_result.raw_text)
                if parsed is not None:
                    return AIAnalysisEnvelope(
                        parsed=parsed,
                        raw_response_text=client_result.raw_text,
                        raw_response_data={
                            **client_result.raw_data,
                            "parsed_response": parsed_obj,
                            "request_payload": payload_dict,
                            "attempt": attempt,
                        },
                        validation_errors=[],
                        fallback_used=False,
                        success=True,
                    )

                last_validation_errors = validation_errors
                last_reason = ";".join(validation_errors) if validation_errors else "ai_parse_failed"
                last_raw_data = {
                    **client_result.raw_data,
                    "parsed_response": parsed_obj,
                }
                log_event(
                    logger,
                    logging.WARNING,
                    "ai_parse_error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    errors=last_reason,
                )

            if attempt < max_attempts:
                sleep(max(0.0, self._config.retry_backoff_seconds) * attempt)

        log_event(
            logger,
            logging.ERROR,
            "ai_fallback_used",
            reason=last_reason,
            max_attempts=max_attempts,
        )
        return self._fallback_envelope(
            reason=last_reason,
            payload=payload_dict,
            raw_text=last_raw_text,
            raw_data=last_raw_data,
            validation_errors=last_validation_errors,
        )

    def _fallback_envelope(
        self,
        reason: str,
        payload: Dict[str, Any],
        raw_text: str,
        raw_data: Dict[str, Any],
        validation_errors: Optional[list[str]] = None,
    ) -> AIAnalysisEnvelope:
        title = str(payload.get("post_title", "")).lower()
        query = str(payload.get("product_query", "")).lower()
        relevance = 0.7 if query and query in title else 0.45

        fallback = AIParsedAnalysis(
            post_meaning="AI unavailable. Fallback interpretation from local heuristics.",
            seller_intent="unknown",
            reliability_signals=[],
            pros=[],
            cons=[],
            warning_signs=["ai_unavailable_or_invalid"],
            recommendation="consider",
            image_product_match="unclear",
            logic_notes=f"fallback_reason:{reason}",
            relevance_score=relevance,
        )

        return AIAnalysisEnvelope(
            parsed=fallback,
            raw_response_text=raw_text,
            raw_response_data={
                **raw_data,
                "request_payload": payload,
                "fallback_reason": reason,
            },
            validation_errors=validation_errors or ([] if not reason else [reason]),
            fallback_used=True,
            success=False,
        )

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

        max_attempts = max(1, self._config.retry_attempts + 1)
        last_raw_text = ""
        last_raw_data: Dict[str, Any] = {}
        last_errors: list[str] = []

        for attempt in range(1, max_attempts + 1):
            client_result = self._ai_client.generate(prompt)
            last_raw_text = client_result.raw_text
            last_raw_data = dict(client_result.raw_data)

            if client_result.error:
                last_errors = [client_result.error]
                log_event(
                    logger,
                    logging.WARNING,
                    "ai_client_error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=client_result.error,
                )
            else:
                parsed, validation_errors, parsed_obj = parse_ai_response(client_result.raw_text)
                if parsed is not None:
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

                last_errors = validation_errors or ["ai_parse_failed"]
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
                    errors=";".join(last_errors),
                )

            if attempt < max_attempts:
                sleep(max(0.0, self._config.retry_backoff_seconds) * attempt)

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

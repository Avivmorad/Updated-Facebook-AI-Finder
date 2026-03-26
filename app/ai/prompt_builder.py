import json
from typing import Any, Dict

from app.domain.ai import AIPromptPacket, AIRequestPayload


def build_ai_prompt(payload: AIRequestPayload) -> AIPromptPacket:
    expected_schema = expected_ai_response_schema()

    system_prompt = (
        "You analyze a Facebook groups post against a user query. "
        "Return only valid JSON using the exact schema provided. "
        "Do not include markdown or extra keys. "
        "You are allowed to judge relevance and match quality only."
    )

    user_prompt = (
        "Analyze this Facebook groups post and return JSON.\n"
        "Determine whether the post is relevant to the user query, what item the post appears to offer, "
        "why it matches or does not match, the match score, and your confidence.\n\n"
        "INPUT_PAYLOAD:\n"
        + json.dumps(payload.to_dict(), ensure_ascii=True, indent=2)
        + "\n\nEXPECTED_SCHEMA:\n"
        + json.dumps(expected_schema, ensure_ascii=True, indent=2)
    )

    return AIPromptPacket(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        expected_schema=expected_schema,
    )


def expected_ai_response_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "is_relevant",
            "match_score",
            "detected_item",
            "match_reason",
            "confidence",
        ],
        "properties": {
            "is_relevant": {"type": "boolean"},
            "match_score": {"type": "number", "minimum": 0, "maximum": 100},
            "detected_item": {"type": "string"},
            "match_reason": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 100},
        },
        "additionalProperties": False,
    }

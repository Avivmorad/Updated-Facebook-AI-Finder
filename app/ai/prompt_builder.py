import json
from typing import Any, Dict

from app.models.ai_models import AIPromptPacket, AIRequestPayload


def build_ai_prompt(payload: AIRequestPayload) -> AIPromptPacket:
    expected_schema = expected_ai_response_schema()

    system_prompt = (
        "You are an assistant that analyzes a marketplace post. "
        "Return only valid JSON using the exact schema provided. "
        "Do not include markdown, comments, or extra keys. "
        "MVP rule: do not infer physical condition from images; "
        "only judge whether image content appears to match the product listing context."
    )

    user_prompt = (
        "Analyze this marketplace post and return JSON.\\n"
        "Fields to analyze:\\n"
        "- post meaning\\n"
        "- seller intent\\n"
        "- reliability signals\\n"
        "- pros\\n"
        "- cons\\n"
        "- warning signs\\n"
        "- recommendation\\n"
        "- whether images seem to match the product\\n\\n"
        "INPUT_PAYLOAD:\\n"
        + json.dumps(payload.to_dict(), ensure_ascii=True, indent=2)
        + "\\n\\nEXPECTED_SCHEMA:\\n"
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
            "post_meaning",
            "seller_intent",
            "reliability_signals",
            "pros",
            "cons",
            "warning_signs",
            "recommendation",
            "image_product_match",
            "logic_notes",
            "relevance_score",
        ],
        "properties": {
            "post_meaning": {"type": "string"},
            "seller_intent": {"type": "string"},
            "reliability_signals": {"type": "array", "items": {"type": "string"}},
            "pros": {"type": "array", "items": {"type": "string"}},
            "cons": {"type": "array", "items": {"type": "string"}},
            "warning_signs": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string", "enum": ["buy", "consider", "skip"]},
            "image_product_match": {"type": "string", "enum": ["match", "mismatch", "unclear"]},
            "logic_notes": {"type": "string"},
            "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "additionalProperties": False,
    }

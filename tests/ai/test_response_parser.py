from app.ai.response_parser import parse_ai_response


def test_parse_ai_response_accepts_spec_schema():
    parsed, errors, _ = parse_ai_response(
        """
        {
          "is_relevant": true,
          "match_score": 91,
          "detected_item": "iPhone 13",
          "match_reason": "The post explicitly offers an iPhone 13.",
          "confidence": 88,
          "is_recent_24h": true,
          "publish_date_observed": "2 hours ago",
          "publish_date_reason": "Timestamp visible in screenshot",
          "publish_date_confidence": 94
        }
        """
    )

    assert errors == []
    assert parsed is not None
    assert parsed.is_relevant is True
    assert parsed.match_score == 91.0
    assert parsed.is_recent_24h is True


def test_parse_ai_response_rejects_unexpected_field():
    parsed, errors, _ = parse_ai_response(
        """
        {
          "is_relevant": true,
          "match_score": 91,
          "detected_item": "iPhone 13",
          "match_reason": "match",
          "confidence": 88,
          "is_recent_24h": true,
          "publish_date_observed": "2 hours ago",
          "publish_date_reason": "Visible in screenshot",
          "publish_date_confidence": 93,
          "warning_signs": []
        }
        """
    )

    assert parsed is None
    assert "unexpected_field:warning_signs" in errors


def test_parse_ai_response_extracts_json_from_markdown_fence():
    parsed, errors, _ = parse_ai_response(
        """
        Here is the result:
        ```json
        {
          "is_relevant": false,
          "match_score": 12,
          "detected_item": "unknown",
          "match_reason": "not a match",
          "confidence": 70,
          "is_recent_24h": false,
          "publish_date_observed": "3 days ago",
          "publish_date_reason": "timestamp text",
          "publish_date_confidence": 80
        }
        ```
        """
    )

    assert errors == []
    assert parsed is not None
    assert parsed.is_relevant is False
    assert parsed.is_recent_24h is False

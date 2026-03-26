import pytest

from app.pipeline.query_service import QueryValidationError, validate_raw_query_input


def test_validate_raw_query_input_accepts_query():
    result = validate_raw_query_input({"query": "iphone 13"})
    assert result.query == "iphone 13"


def test_validate_raw_query_input_accepts_legacy_main_text_alias():
    result = validate_raw_query_input({"main_text": "iphone 13"})
    assert result.query == "iphone 13"


def test_validate_raw_query_input_rejects_empty_query():
    with pytest.raises(QueryValidationError):
        validate_raw_query_input({"query": "   "})

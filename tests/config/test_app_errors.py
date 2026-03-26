from app.utils.app_errors import ERROR_CATALOG, make_app_error, render_app_error_text


def test_error_catalog_entries_have_required_fields():
    assert len(ERROR_CATALOG) > 0
    for code, template in ERROR_CATALOG.items():
        assert template.code == code
        assert template.summary_he.strip() != ""
        assert template.cause_he.strip() != ""
        assert template.action_he.strip() != ""
    assert "ERR_FILTER_RECENT_NOT_FOUND" in ERROR_CATALOG
    assert "ERR_FILTER_LAST24_NOT_FOUND" in ERROR_CATALOG
    assert "ERR_POST_PUBLISH_DATE_MISSING" in ERROR_CATALOG
    assert "ERR_AI_RESPONSE_INVALID_JSON" in ERROR_CATALOG
    assert "ERR_POST_SCREENSHOT_MISSING" in ERROR_CATALOG
    assert "ERR_AI_VISION_MODEL_MISSING" in ERROR_CATALOG
    assert "ERR_AI_VISION_MODEL_DECOMMISSIONED" in ERROR_CATALOG


def test_render_app_error_format_is_consistent():
    app_error = make_app_error(
        code="ERR_AI_RESPONSE_INVALID_JSON",
        technical_details="raw_response=not_json",
    )
    text = render_app_error_text(app_error)

    assert "ERR_AI_RESPONSE_INVALID_JSON" in text
    assert "Cause:" in text
    assert "Action:" in text
    assert "Technical details: raw_response=not_json" in text

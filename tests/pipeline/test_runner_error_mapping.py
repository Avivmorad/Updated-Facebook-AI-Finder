from app.pipeline.runner import PipelineRunner


def test_runner_maps_time_filter_reasons_to_specific_error_codes():
    runner = PipelineRunner()
    assert runner._build_time_filter_error("missing_publish_date").code == "ERR_POST_PUBLISH_DATE_MISSING"
    assert runner._build_time_filter_error("unparseable_publish_date").code == "ERR_POST_PUBLISH_DATE_UNPARSEABLE"
    assert runner._build_time_filter_error("older_than_24_hours").code == "ERR_POST_TOO_OLD"


def test_runner_maps_ai_failure_codes():
    runner = PipelineRunner()
    assert runner._infer_ai_failure_code(["ERR_AI_RESPONSE_INVALID_JSON"]) == "ERR_AI_RESPONSE_INVALID_JSON"
    assert runner._infer_ai_failure_code(["ERR_AI_RESPONSE_EMPTY"]) == "ERR_AI_RESPONSE_EMPTY"
    assert runner._infer_ai_failure_code(["ERR_AI_RESPONSE_SCHEMA_INVALID"]) == "ERR_AI_RESPONSE_SCHEMA_INVALID"

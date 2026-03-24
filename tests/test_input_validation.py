import pytest

from app.logic.input_validation import InputValidationError, validate_raw_search_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_base() -> dict:
    """Minimal valid payload that passes all validation rules."""
    return {
        "main_text": "iPhone 13",
        "all_country": True,
    }


def _assert_error_field(exc: InputValidationError, field: str) -> None:
    fields = [e.field for e in exc.errors]
    assert field in fields, f"Expected error on field '{field}', got: {fields}"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_minimal_valid_input_returns_raw_search_input(self):
        result = validate_raw_search_input(_valid_base())
        assert result.main_text == "iPhone 13"

    def test_full_valid_input_returns_expected_values(self):
        payload = {
            "main_text": "  MacBook Pro  ",
            "tags": ["laptop", "apple"],
            "secondary_attributes": ["silver"],
            "forbidden_words": ["broken", "damaged"],
            "min_price": 1000,
            "max_price": 5000,
            "is_free": False,
            "post_age": "7d",
            "require_image": False,
            "language": "en",
            "all_country": True,
            "group_mode": "all_groups",
            "search_name": "My MacBook Search",
        }
        result = validate_raw_search_input(payload)
        assert result.main_text == "MacBook Pro"
        assert result.min_price == 1000.0
        assert result.max_price == 5000.0
        assert result.post_age == "7d"
        assert result.language == "en"
        assert result.search_name == "My MacBook Search"
        assert result.tags == ["laptop", "apple"]

    def test_all_country_true_skips_regions_requirement(self):
        payload = {**_valid_base(), "all_country": True}
        result = validate_raw_search_input(payload)
        assert result.all_country is True

    def test_manual_regions_accepted_without_predefined(self):
        payload = {
            "main_text": "Chair",
            "manual_regions": ["Tel Aviv"],
        }
        result = validate_raw_search_input(payload)
        assert result.manual_regions == ["Tel Aviv"]

    def test_specific_groups_with_groups_list(self):
        payload = {
            **_valid_base(),
            "group_mode": "specific_groups",
            "groups": ["Buy & Sell Israel"],
        }
        result = validate_raw_search_input(payload)
        assert result.group_mode == "specific_groups"
        assert result.groups == ["Buy & Sell Israel"]

    def test_specific_groups_with_select_all_groups(self):
        payload = {
            **_valid_base(),
            "group_mode": "specific_groups",
            "select_all_groups": True,
        }
        result = validate_raw_search_input(payload)
        assert result.select_all_groups is True

    def test_url_input_source_with_group_urls(self):
        payload = {
            **_valid_base(),
            "group_mode": "specific_groups",
            "group_sources": ["url_input"],
            "group_urls": ["https://facebook.com/groups/123"],
        }
        result = validate_raw_search_input(payload)
        assert result.group_urls == ["https://facebook.com/groups/123"]

    def test_duplicate_tags_are_deduplicated(self):
        payload = {**_valid_base(), "tags": ["apple", "Apple", "APPLE"]}
        result = validate_raw_search_input(payload)
        assert len(result.tags) == 1
        assert result.tags[0] == "apple"


# ---------------------------------------------------------------------------
# main_text errors
# ---------------------------------------------------------------------------


class TestMainTextErrors:
    def test_missing_main_text_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({"all_country": True})
        _assert_error_field(exc_info.value, "main_text")

    def test_empty_main_text_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({"main_text": "   ", "all_country": True})
        _assert_error_field(exc_info.value, "main_text")

    def test_non_string_main_text_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({"main_text": 42, "all_country": True})
        _assert_error_field(exc_info.value, "main_text")

    def test_none_main_text_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({"main_text": None, "all_country": True})
        _assert_error_field(exc_info.value, "main_text")


# ---------------------------------------------------------------------------
# Price validation errors
# ---------------------------------------------------------------------------


class TestPriceValidationErrors:
    def test_negative_min_price_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "min_price": -1})
        _assert_error_field(exc_info.value, "min_price")

    def test_negative_max_price_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "max_price": -10.0})
        _assert_error_field(exc_info.value, "max_price")

    def test_min_greater_than_max_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {**_valid_base(), "min_price": 500, "max_price": 100}
            )
        _assert_error_field(exc_info.value, "price_range")

    def test_is_free_with_nonzero_min_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {**_valid_base(), "is_free": True, "min_price": 100}
            )
        _assert_error_field(exc_info.value, "is_free")

    def test_is_free_with_nonzero_max_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {**_valid_base(), "is_free": True, "max_price": 200}
            )
        _assert_error_field(exc_info.value, "is_free")

    def test_is_free_with_zero_prices_is_valid(self):
        result = validate_raw_search_input(
            {**_valid_base(), "is_free": True, "min_price": 0, "max_price": 0}
        )
        assert result.is_free is True

    def test_bool_as_price_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "min_price": True})
        _assert_error_field(exc_info.value, "min_price")

    def test_string_as_price_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "max_price": "500"})
        _assert_error_field(exc_info.value, "max_price")


# ---------------------------------------------------------------------------
# post_age validation
# ---------------------------------------------------------------------------


class TestPostAgeValidation:
    def test_invalid_post_age_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "post_age": "yesterday"})
        _assert_error_field(exc_info.value, "post_age")

    def test_all_valid_post_age_options(self):
        for option in ["1h", "24h", "3d", "7d", "30d"]:
            result = validate_raw_search_input({**_valid_base(), "post_age": option})
            assert result.post_age == option


# ---------------------------------------------------------------------------
# forbidden_words validation
# ---------------------------------------------------------------------------


class TestForbiddenWordsValidation:
    def test_invalid_forbidden_word_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {**_valid_base(), "forbidden_words": ["garbage_word"]}
            )
        _assert_error_field(exc_info.value, "forbidden_words")

    def test_valid_forbidden_words_accepted(self):
        result = validate_raw_search_input(
            {**_valid_base(), "forbidden_words": ["broken", "fake"]}
        )
        assert "broken" in result.forbidden_words
        assert "fake" in result.forbidden_words

    def test_forbidden_words_case_insensitive(self):
        result = validate_raw_search_input(
            {**_valid_base(), "forbidden_words": ["BROKEN", "Fake"]}
        )
        assert len(result.forbidden_words) == 2


# ---------------------------------------------------------------------------
# regions validation
# ---------------------------------------------------------------------------


class TestRegionsValidation:
    def test_invalid_region_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    "main_text": "Chair",
                    "regions": ["moon_base"],
                }
            )
        _assert_error_field(exc_info.value, "regions")

    def test_all_country_with_regions_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    "main_text": "Chair",
                    "all_country": True,
                    "regions": ["north"],
                }
            )
        _assert_error_field(exc_info.value, "all_country")

    def test_all_country_with_manual_regions_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    "main_text": "Chair",
                    "all_country": True,
                    "manual_regions": ["Holon"],
                }
            )
        _assert_error_field(exc_info.value, "all_country")

    def test_no_regions_and_no_all_country_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({"main_text": "Chair"})
        _assert_error_field(exc_info.value, "regions")

    def test_valid_predefined_regions_accepted(self):
        result = validate_raw_search_input(
            {
                "main_text": "Chair",
                "regions": ["north", "center", "south"],
            }
        )
        assert result.regions == ["north", "center", "south"]


# ---------------------------------------------------------------------------
# group inputs validation
# ---------------------------------------------------------------------------


class TestGroupInputsValidation:
    def test_invalid_group_mode_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "group_mode": "unknown_mode"})
        _assert_error_field(exc_info.value, "group_mode")

    def test_invalid_group_source_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    **_valid_base(),
                    "group_mode": "specific_groups",
                    "group_sources": ["invalid_source"],
                    "groups": ["some group"],
                }
            )
        _assert_error_field(exc_info.value, "group_sources")

    def test_specific_groups_without_any_target_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {**_valid_base(), "group_mode": "specific_groups"}
            )
        _assert_error_field(exc_info.value, "groups")

    def test_url_input_source_without_urls_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    **_valid_base(),
                    "group_mode": "specific_groups",
                    "group_sources": ["url_input"],
                }
            )
        _assert_error_field(exc_info.value, "group_urls")


# ---------------------------------------------------------------------------
# String list field parsing
# ---------------------------------------------------------------------------


class TestStringListParsing:
    def test_non_list_tags_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "tags": "laptop"})
        _assert_error_field(exc_info.value, "tags")

    def test_non_string_item_in_list_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "tags": ["laptop", 42]})
        _assert_error_field(exc_info.value, "tags[1]")

    def test_empty_strings_in_list_are_filtered(self):
        result = validate_raw_search_input(
            {**_valid_base(), "tags": ["", "  ", "laptop"]}
        )
        assert result.tags == ["laptop"]

    def test_none_list_falls_back_to_empty(self):
        result = validate_raw_search_input({**_valid_base(), "tags": None})
        assert result.tags == []


# ---------------------------------------------------------------------------
# Bool field parsing
# ---------------------------------------------------------------------------


class TestBoolFieldParsing:
    def test_non_bool_require_image_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "require_image": "yes"})
        _assert_error_field(exc_info.value, "require_image")

    def test_non_bool_is_free_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "is_free": 1})
        _assert_error_field(exc_info.value, "is_free")


# ---------------------------------------------------------------------------
# Optional string field
# ---------------------------------------------------------------------------


class TestOptionalStringField:
    def test_non_string_search_name_raises(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({**_valid_base(), "search_name": 123})
        _assert_error_field(exc_info.value, "search_name")

    def test_empty_search_name_returns_none(self):
        result = validate_raw_search_input({**_valid_base(), "search_name": "   "})
        assert result.search_name is None

    def test_none_search_name_returns_none(self):
        result = validate_raw_search_input({**_valid_base()})
        assert result.search_name is None


# ---------------------------------------------------------------------------
# Error message formatting
# ---------------------------------------------------------------------------


class TestErrorFormatting:
    def test_exception_str_contains_field_names(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({})
        assert "main_text" in str(exc_info.value)

    def test_to_dict_contains_errors_key(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input({})
        d = exc_info.value.to_dict()
        assert "errors" in d
        assert isinstance(d["errors"], list)

    def test_multiple_errors_collected_before_raising(self):
        with pytest.raises(InputValidationError) as exc_info:
            validate_raw_search_input(
                {
                    "main_text": "",
                    "min_price": -5,
                }
            )
        assert len(exc_info.value.errors) >= 2

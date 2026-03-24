from app.scraper.post_normalizer import (
    normalize_post_data,
    _clean_text,
    _clean_string_list,
    _parse_price,
    _extract_age_token,
    _extract_date_token,
)


# ---------------------------------------------------------------------------
# normalize_post_data — full round-trip
# ---------------------------------------------------------------------------


class TestNormalizePostData:
    def _full_raw(self) -> dict:
        return {
            "post_id": "  abc123  ",
            "url": "  https://fb.com/post/1  ",
            "title_text": "  iPhone 13 Pro  ",
            "post_text": "  Selling my iPhone  ",
            "price_text": "₪ 3,500",
            "location_text": "  Tel Aviv  ",
            "publish_text": "2 days ago",
            "seller_name": "  Alice  ",
            "image_urls": ["img1.jpg", "img2.jpg"],
            "comments": ["Great deal!", "Is it still available?"],
            "important_visible_signals": ["Like new condition"],
        }

    def test_all_fields_populated(self):
        result = normalize_post_data(self._full_raw())
        assert result["post_id"] == "abc123"
        assert result["url"] == "https://fb.com/post/1"
        assert result["title"] == "iPhone 13 Pro"
        assert result["text"] == "Selling my iPhone"
        assert result["price"] == 3500.0
        assert result["currency"] == "₪"
        assert result["location"] == "Tel Aviv"
        assert result["seller_name"] == "Alice"
        assert result["images"] == ["img1.jpg", "img2.jpg"]
        assert result["images_count"] == 2
        assert result["has_image"] is True
        assert result["comments_count"] == 2
        assert result["important_visible_signals"] == ["Like new condition"]

    def test_missing_optional_fields_return_defaults(self):
        result = normalize_post_data({"title_text": "Chair"})
        assert result["post_id"] == ""
        assert result["url"] == ""
        assert result["price"] is None
        assert result["currency"] is None
        assert result["location"] is None
        assert result["images"] == []
        assert result["images_count"] == 0
        assert result["has_image"] is False
        assert result["comments"] == []
        assert result["comments_count"] == 0
        assert result["important_visible_signals"] == []

    def test_empty_dict_returns_safe_defaults(self):
        result = normalize_post_data({})
        assert result["title"] == ""
        assert result["text"] == ""

    def test_publish_age_token_extracted(self):
        result = normalize_post_data({"title_text": "x", "publish_text": "3 hours ago"})
        assert result["publish_age"] == "3 hours ago"
        assert result["publish_date"] is None

    def test_publish_date_token_extracted(self):
        result = normalize_post_data(
            {"title_text": "x", "publish_text": "Jan 15, 2024"}
        )
        assert result["publish_date"] == "Jan 15, 2024"


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------


class TestParsePrice:
    def test_shekel_symbol(self):
        price, currency = _parse_price("₪ 1,500")
        assert price == 1500.0
        assert currency == "₪"

    def test_dollar_symbol(self):
        price, currency = _parse_price("$250.99")
        assert price == 250.99
        assert currency == "$"

    def test_euro_symbol(self):
        price, currency = _parse_price("€ 800")
        assert price == 800.0
        assert currency == "€"

    def test_no_symbol(self):
        price, currency = _parse_price("4000")
        assert price == 4000.0
        assert currency is None

    def test_comma_separated_number(self):
        price, currency = _parse_price("10,000")
        assert price == 10000.0

    def test_none_input_returns_none_none(self):
        price, currency = _parse_price(None)
        assert price is None
        assert currency is None

    def test_empty_string_returns_none_none(self):
        price, currency = _parse_price("")
        assert price is None
        assert currency is None

    def test_text_only_no_digit_returns_none(self):
        price, currency = _parse_price("Free")
        assert price is None
        assert currency is None

    def test_price_at_start_of_phrase(self):
        price, currency = _parse_price("₪2,000 negotiable")
        assert price == 2000.0
        assert currency == "₪"


# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


class TestCleanText:
    def test_strips_whitespace(self):
        assert _clean_text("  hello  ") == "hello"

    def test_empty_string_returns_none(self):
        assert _clean_text("") is None

    def test_whitespace_only_returns_none(self):
        assert _clean_text("   ") is None

    def test_none_returns_none(self):
        assert _clean_text(None) is None

    def test_non_string_converted(self):
        assert _clean_text(42) == "42"


# ---------------------------------------------------------------------------
# _clean_string_list
# ---------------------------------------------------------------------------


class TestCleanStringList:
    def test_strips_and_returns_items(self):
        assert _clean_string_list(["  a  ", "  b  "]) == ["a", "b"]

    def test_removes_empty_items(self):
        assert _clean_string_list(["", "  ", "valid"]) == ["valid"]

    def test_deduplicates_case_insensitively(self):
        result = _clean_string_list(["Hello", "hello", "HELLO"])
        assert len(result) == 1
        assert result[0] == "Hello"

    def test_non_list_returns_empty(self):
        assert _clean_string_list("not a list") == []  # type: ignore[arg-type]

    def test_empty_list_returns_empty(self):
        assert _clean_string_list([]) == []


# ---------------------------------------------------------------------------
# _extract_age_token
# ---------------------------------------------------------------------------


class TestExtractAgeToken:
    def test_hours_matched(self):
        assert _extract_age_token("2 hours ago") == "2 hours ago"

    def test_days_matched(self):
        assert _extract_age_token("3 days ago") == "3 days ago"

    def test_week_matched(self):
        assert _extract_age_token("1 week ago") == "1 week ago"

    def test_today_matched(self):
        assert _extract_age_token("Today") == "Today"

    def test_yesterday_matched(self):
        assert _extract_age_token("Yesterday") == "Yesterday"

    def test_date_string_not_matched(self):
        assert _extract_age_token("Jan 15, 2024") is None

    def test_none_returns_none(self):
        assert _extract_age_token(None) is None


# ---------------------------------------------------------------------------
# _extract_date_token
# ---------------------------------------------------------------------------


class TestExtractDateToken:
    def test_slash_separator_matched(self):
        assert _extract_date_token("15/01/2024") == "15/01/2024"

    def test_dash_separator_matched(self):
        assert _extract_date_token("2024-01-15") == "2024-01-15"

    def test_month_name_matched(self):
        assert _extract_date_token("Jan 15") == "Jan 15"

    def test_december_matched(self):
        assert _extract_date_token("Dec 31") == "Dec 31"

    def test_plain_age_text_not_matched(self):
        assert _extract_date_token("3 days ago") is None

    def test_none_returns_none(self):
        assert _extract_date_token(None) is None

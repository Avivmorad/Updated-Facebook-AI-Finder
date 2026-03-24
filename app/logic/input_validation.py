from typing import Any, Dict, List, Optional

from app.models.input_models import RawSearchInput, ValidationErrorItem
from config.input_config import (
    DEFAULT_GROUP_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_POST_AGE,
    DEFAULT_REQUIRE_IMAGE,
    FIXED_FORBIDDEN_WORDS,
    GROUP_MODES,
    GROUP_SOURCES,
    POST_AGE_OPTIONS,
    REGION_OPTIONS,
)


class InputValidationError(Exception):
    def __init__(self, errors: List[ValidationErrorItem]) -> None:
        self.errors = errors
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        return "; ".join([f"{e.field}: {e.message}" for e in self.errors])

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        return {"errors": [error.to_dict() for error in self.errors]}


def validate_raw_search_input(raw_input: Dict[str, Any]) -> RawSearchInput:
    errors: List[ValidationErrorItem] = []

    main_text = _require_non_empty_string(raw_input, "main_text", errors)
    tags = _read_string_list(raw_input, "tags", errors)
    secondary_attributes = _read_string_list(raw_input, "secondary_attributes", errors)
    forbidden_words = _read_string_list(raw_input, "forbidden_words", errors)

    min_price = _read_optional_number(raw_input, "min_price", errors)
    max_price = _read_optional_number(raw_input, "max_price", errors)
    is_free = _read_bool(raw_input, "is_free", False, errors)

    post_age = _read_string(raw_input, "post_age", DEFAULT_POST_AGE, errors)
    require_image = _read_bool(raw_input, "require_image", DEFAULT_REQUIRE_IMAGE, errors)
    language = _read_string(raw_input, "language", DEFAULT_LANGUAGE, errors)

    regions = _read_string_list(raw_input, "regions", errors)
    manual_regions = _read_string_list(raw_input, "manual_regions", errors)
    all_country = _read_bool(raw_input, "all_country", False, errors)

    group_mode = _read_string(raw_input, "group_mode", DEFAULT_GROUP_MODE, errors)
    groups = _read_string_list(raw_input, "groups", errors)
    group_sources = _read_string_list(raw_input, "group_sources", errors)
    group_urls = _read_string_list(raw_input, "group_urls", errors)
    select_all_groups = _read_bool(raw_input, "select_all_groups", False, errors)

    search_name = _read_optional_string(raw_input, "search_name", errors)

    _validate_prices(min_price, max_price, is_free, errors)
    _validate_post_age(post_age, errors)
    _validate_forbidden_words(forbidden_words, errors)
    _validate_regions(regions, manual_regions, all_country, errors)
    _validate_group_inputs(group_mode, groups, group_sources, group_urls, select_all_groups, errors)

    if errors:
        raise InputValidationError(errors)

    return RawSearchInput(
        main_text=main_text,
        tags=tags,
        secondary_attributes=secondary_attributes,
        forbidden_words=forbidden_words,
        min_price=min_price,
        max_price=max_price,
        is_free=is_free,
        post_age=post_age,
        require_image=require_image,
        language=language,
        regions=regions,
        manual_regions=manual_regions,
        all_country=all_country,
        group_mode=group_mode,
        groups=groups,
        group_sources=group_sources,
        group_urls=group_urls,
        select_all_groups=select_all_groups,
        search_name=search_name,
    )


def _require_non_empty_string(source: Dict[str, Any], key: str, errors: List[ValidationErrorItem]) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(ValidationErrorItem(field=key, message="must be a non-empty string"))
        return ""
    return value.strip()


def _read_string(source: Dict[str, Any], key: str, default: str, errors: List[ValidationErrorItem]) -> str:
    value = source.get(key, default)
    if not isinstance(value, str):
        errors.append(ValidationErrorItem(field=key, message="must be a string"))
        return default
    return value.strip() or default


def _read_optional_string(
    source: Dict[str, Any], key: str, errors: List[ValidationErrorItem]
) -> Optional[str]:
    value = source.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(ValidationErrorItem(field=key, message="must be a string when provided"))
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _read_string_list(source: Dict[str, Any], key: str, errors: List[ValidationErrorItem]) -> List[str]:
    value = source.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(ValidationErrorItem(field=key, message="must be a list of strings"))
        return []

    cleaned: List[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                ValidationErrorItem(
                    field=f"{key}[{index}]", message="must be a string"
                )
            )
            continue
        item_value = item.strip()
        if item_value:
            cleaned.append(item_value)

    # Keep order while removing duplicates.
    deduped: List[str] = []
    seen = set()
    for item in cleaned:
        if item.lower() not in seen:
            seen.add(item.lower())
            deduped.append(item)

    return deduped


def _read_optional_number(
    source: Dict[str, Any], key: str, errors: List[ValidationErrorItem]
) -> Optional[float]:
    value = source.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(ValidationErrorItem(field=key, message="must be a number"))
        return None
    if isinstance(value, (int, float)):
        return float(value)
    errors.append(ValidationErrorItem(field=key, message="must be a number"))
    return None


def _read_bool(
    source: Dict[str, Any], key: str, default: bool, errors: List[ValidationErrorItem]
) -> bool:
    value = source.get(key, default)
    if isinstance(value, bool):
        return value
    errors.append(ValidationErrorItem(field=key, message="must be a boolean"))
    return default


def _validate_prices(
    min_price: Optional[float],
    max_price: Optional[float],
    is_free: bool,
    errors: List[ValidationErrorItem],
) -> None:
    if min_price is not None and min_price < 0:
        errors.append(ValidationErrorItem(field="min_price", message="must be >= 0"))
    if max_price is not None and max_price < 0:
        errors.append(ValidationErrorItem(field="max_price", message="must be >= 0"))

    if min_price is not None and max_price is not None and min_price > max_price:
        errors.append(
            ValidationErrorItem(
                field="price_range", message="min_price cannot be greater than max_price"
            )
        )

    if is_free and ((min_price not in (None, 0.0)) or (max_price not in (None, 0.0))):
        errors.append(
            ValidationErrorItem(
                field="is_free",
                message="when is_free is true, min_price and max_price must be empty or 0",
            )
        )


def _validate_post_age(post_age: str, errors: List[ValidationErrorItem]) -> None:
    if post_age not in POST_AGE_OPTIONS:
        valid_options = ", ".join(POST_AGE_OPTIONS.keys())
        errors.append(
            ValidationErrorItem(
                field="post_age",
                message=f"must be one of predefined options: {valid_options}",
            )
        )


def _validate_forbidden_words(
    forbidden_words: List[str], errors: List[ValidationErrorItem]
) -> None:
    allowed_lower = {word.lower() for word in FIXED_FORBIDDEN_WORDS}
    invalid_words = [word for word in forbidden_words if word.lower() not in allowed_lower]
    if invalid_words:
        errors.append(
            ValidationErrorItem(
                field="forbidden_words",
                message=(
                    "contains unsupported values: "
                    + ", ".join(invalid_words)
                    + ". Use fixed list only"
                ),
            )
        )


def _validate_regions(
    regions: List[str],
    manual_regions: List[str],
    all_country: bool,
    errors: List[ValidationErrorItem],
) -> None:
    allowed_regions = {region.lower() for region in REGION_OPTIONS}

    invalid_from_list = [region for region in regions if region.lower() not in allowed_regions]
    if invalid_from_list:
        errors.append(
            ValidationErrorItem(
                field="regions",
                message=(
                    "contains unsupported regions: "
                    + ", ".join(invalid_from_list)
                    + ". Use predefined list or manual_regions"
                ),
            )
        )

    if all_country and (regions or manual_regions):
        errors.append(
            ValidationErrorItem(
                field="all_country",
                message="cannot be true together with regions/manual_regions",
            )
        )

    if not all_country and not regions and not manual_regions:
        errors.append(
            ValidationErrorItem(
                field="regions",
                message="select at least one region, add manual region, or set all_country=true",
            )
        )


def _validate_group_inputs(
    group_mode: str,
    groups: List[str],
    group_sources: List[str],
    group_urls: List[str],
    select_all_groups: bool,
    errors: List[ValidationErrorItem],
) -> None:
    if group_mode not in GROUP_MODES:
        errors.append(
            ValidationErrorItem(
                field="group_mode",
                message=f"must be one of: {', '.join(GROUP_MODES)}",
            )
        )

    allowed_sources = {source.lower() for source in GROUP_SOURCES}
    invalid_sources = [source for source in group_sources if source.lower() not in allowed_sources]
    if invalid_sources:
        errors.append(
            ValidationErrorItem(
                field="group_sources",
                message="contains unsupported sources: " + ", ".join(invalid_sources),
            )
        )

    if group_mode == "specific_groups":
        has_sources = bool(group_sources)
        has_groups = bool(groups)
        has_urls = bool(group_urls)

        if not select_all_groups and not (has_groups or has_urls or has_sources):
            errors.append(
                ValidationErrorItem(
                    field="groups",
                    message=(
                        "for specific_groups provide groups, or group_urls, or group_sources, "
                        "or select_all_groups=true"
                    ),
                )
            )

        if "url_input" in [source.lower() for source in group_sources] and not has_urls:
            errors.append(
                ValidationErrorItem(
                    field="group_urls",
                    message="group_urls is required when group_sources includes url_input",
                )
            )

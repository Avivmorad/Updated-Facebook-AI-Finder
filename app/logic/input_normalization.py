from typing import List

from app.models.input_models import RawSearchInput, SearchRequest
from config.input_config import DEFAULT_LANGUAGE


def normalize_to_search_request(valid_input: RawSearchInput) -> SearchRequest:
    language = (valid_input.language or DEFAULT_LANGUAGE).strip().lower()

    target_regions = _merge_regions(valid_input.regions, valid_input.manual_regions)

    if valid_input.is_free:
        min_price = None
        max_price = 0.0
    else:
        min_price = valid_input.min_price
        max_price = valid_input.max_price

    return SearchRequest(
        query_text=valid_input.main_text.strip(),
        tags=_normalize_text_list(valid_input.tags),
        secondary_attributes=_normalize_text_list(valid_input.secondary_attributes),
        forbidden_words=_normalize_text_list(valid_input.forbidden_words),
        min_price=min_price,
        max_price=max_price,
        is_free=valid_input.is_free,
        post_age=valid_input.post_age,
        require_image=valid_input.require_image,
        language=language,
        target_regions=target_regions,
        all_country=valid_input.all_country,
        group_mode=valid_input.group_mode,
        groups=_normalize_text_list(valid_input.groups),
        group_sources=_normalize_text_list(valid_input.group_sources),
        group_urls=_normalize_text_list(valid_input.group_urls),
        select_all_groups=valid_input.select_all_groups,
    )


def _normalize_text_list(values: List[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _merge_regions(predefined_regions: List[str], manual_regions: List[str]) -> List[str]:
    merged = _normalize_text_list(predefined_regions) + _normalize_text_list(manual_regions)

    result: List[str] = []
    seen = set()
    for item in merged:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result

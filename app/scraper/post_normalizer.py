import re
from typing import Any, Dict, List, Optional


_PRICE_REGEX = re.compile(r"([₪$€])?\s*([0-9][0-9,]*(?:\.[0-9]+)?)")


def normalize_post_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    title = _clean_text(raw_data.get("title_text"))
    post_text = _clean_text(raw_data.get("post_text"))
    price_text = _clean_text(raw_data.get("price_text"))
    location = _clean_text(raw_data.get("location_text"))
    publish_text = _clean_text(raw_data.get("publish_text"))
    seller_name = _clean_text(raw_data.get("seller_name"))

    price_value, currency = _parse_price(price_text)

    image_urls = _clean_string_list(raw_data.get("image_urls", []))
    comments = _clean_string_list(raw_data.get("comments", []))
    signals = _clean_string_list(raw_data.get("important_visible_signals", []))

    return {
        "post_id": _clean_text(raw_data.get("post_id")) or "",
        "url": _clean_text(raw_data.get("url")) or "",
        "title": title or "",
        "text": post_text or "",
        "price": price_value,
        "currency": currency,
        "price_text": price_text,
        "location": location,
        "publish_age": _extract_age_token(publish_text),
        "publish_date": _extract_date_token(publish_text),
        "publish_text": publish_text,
        "images": image_urls,
        "images_count": len(image_urls),
        "has_image": bool(image_urls),
        "seller_name": seller_name,
        "comments": comments,
        "comments_count": len(comments),
        "important_visible_signals": signals,
    }


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _clean_string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []

    output: List[str] = []
    seen = set()
    for item in values:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)

    return output


def _parse_price(price_text: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    if not price_text:
        return None, None

    match = _PRICE_REGEX.search(price_text)
    if match is None:
        return None, None

    currency = match.group(1)
    number = match.group(2).replace(",", "")
    try:
        return float(number), currency
    except ValueError:
        return None, currency


def _extract_age_token(publish_text: Optional[str]) -> Optional[str]:
    if not publish_text:
        return None

    lowered = publish_text.lower()
    markers = ["hour", "day", "week", "month", "year", "hr", "min", "today", "yesterday"]
    if any(marker in lowered for marker in markers):
        return publish_text
    return None


def _extract_date_token(publish_text: Optional[str]) -> Optional[str]:
    if not publish_text:
        return None

    # Keep raw date-like text when it contains separators or month names.
    lowered = publish_text.lower()
    has_separator = "/" in publish_text or "-" in publish_text
    month_markers = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    if has_separator or any(marker in lowered for marker in month_markers):
        return publish_text
    return None

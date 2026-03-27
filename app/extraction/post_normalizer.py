from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.domain.posts import CollectedPost


_SPACE_PATTERN = re.compile(r"\s+")


def normalize_post_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    post_link = _clean_text(raw_data.get("post_link"))
    post_id = _clean_text(raw_data.get("post_id")) or _extract_post_id(post_link)
    post_text = _clean_text(raw_data.get("post_text"), normalize_whitespace=True)
    images = _clean_string_list(raw_data.get("images", []))
    publish_raw = _clean_publish_text(raw_data.get("publish_date_raw", raw_data.get("publish_date", "")))
    publish_normalized = _clean_publish_text(raw_data.get("publish_date_normalized", publish_raw))
    screenshot_path = _clean_text(raw_data.get("post_screenshot_path"))
    screenshot_paths = _clean_string_list(raw_data.get("screenshot_paths", []))
    if screenshot_path and screenshot_path not in screenshot_paths:
        screenshot_paths.insert(0, screenshot_path)

    collected = CollectedPost(
        post_link=post_link,
        post_id=post_id,
        post_text=post_text,
        images=images,
        image_count=len(images),
        publish_date_raw=publish_raw,
        publish_date_normalized=publish_normalized,
        extraction_quality=_infer_extraction_quality(
            post_link=post_link,
            post_text=post_text,
            image_count=len(images),
            publish_date=publish_normalized or publish_raw,
        ),
        post_screenshot_path=screenshot_path,
        screenshot_paths=screenshot_paths,
    )
    return collected.to_dict()


def _clean_text(value: Any, *, normalize_whitespace: bool = False) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if normalize_whitespace:
        text = _SPACE_PATTERN.sub(" ", text)
    return text


def _clean_publish_text(value: Any) -> str:
    return (
        _clean_text(value, normalize_whitespace=True)
        .replace("\u200e", "")
        .replace("\u200f", "")
        .replace("\u202a", "")
        .replace("\u202b", "")
        .replace("\u202c", "")
        .strip()
    )


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


def _infer_extraction_quality(
    *,
    post_link: str,
    post_text: str,
    image_count: int,
    publish_date: str,
) -> str:
    if not post_link:
        return "failed"
    signal_count = 0
    if post_text:
        signal_count += 1
    if image_count > 0:
        signal_count += 1
    if publish_date:
        signal_count += 1

    if signal_count >= 3:
        return "good"
    if signal_count >= 1:
        return "partial"
    return "failed"


def _extract_post_id(post_link: str) -> str:
    link = _clean_text(post_link)
    if not link:
        return ""
    for marker in ("/posts/", "/permalink/"):
        if marker in link:
            suffix = link.split(marker, 1)[1]
            return suffix.split("/", 1)[0].split("?", 1)[0]
    try:
        parsed = urlparse(link)
    except ValueError:
        return ""
    return parsed.path.rstrip("/").split("/")[-1]

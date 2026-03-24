from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RawSearchInput:
    main_text: str
    tags: List[str] = field(default_factory=list)
    secondary_attributes: List[str] = field(default_factory=list)
    forbidden_words: List[str] = field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    is_free: bool = False
    post_age: str = "24h"
    require_image: bool = True
    language: str = "he"
    regions: List[str] = field(default_factory=list)
    manual_regions: List[str] = field(default_factory=list)
    all_country: bool = False
    group_mode: str = "all_groups"
    groups: List[str] = field(default_factory=list)
    group_sources: List[str] = field(default_factory=lambda: ["user_groups"])
    group_urls: List[str] = field(default_factory=list)
    select_all_groups: bool = False
    search_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchRequest:
    query_text: str
    tags: List[str]
    secondary_attributes: List[str]
    forbidden_words: List[str]
    min_price: Optional[float]
    max_price: Optional[float]
    is_free: bool
    post_age: str
    require_image: bool
    language: str
    target_regions: List[str]
    all_country: bool
    group_mode: str
    groups: List[str]
    group_sources: List[str]
    group_urls: List[str]
    select_all_groups: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SavedSearch:
    name: str
    created_at: str
    input_payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationErrorItem:
    field: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"field": self.field, "message": self.message}

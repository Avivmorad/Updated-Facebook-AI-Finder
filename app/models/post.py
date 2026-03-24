from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Post:
    raw_post_data: Dict[str, Any] = field(default_factory=dict)
    normalized_post_data: Dict[str, Any] = field(default_factory=dict)
    analysis: Dict[str, Any] = field(default_factory=dict)
    scoring: Dict[str, Any] = field(default_factory=dict)

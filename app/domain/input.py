from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class UserQuery:
    query: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationErrorItem:
    field: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"field": self.field, "message": self.message}

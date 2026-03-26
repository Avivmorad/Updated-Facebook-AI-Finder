from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PresentationConfig:
    summary_preview_max_length: int = 120


@dataclass(frozen=True)
class RunHistoryConfig:
    history_file_path: str = str(Path("data") / "run_history.json")
    max_saved_runs: int = 100

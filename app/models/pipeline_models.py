from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StageStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ProgressState:
    current_stage: str = "pending"
    completed_stages: int = 0
    total_stages: int = 9
    processed_posts: int = 0
    max_posts: int = 20
    percentage: float = 0.0

    def update_stage_progress(self) -> None:
        if self.total_stages <= 0:
            self.percentage = 0.0
            return
        base = (self.completed_stages / self.total_stages) * 100.0
        self.percentage = min(100.0, round(base, 2))

    @property
    def post_counter(self) -> str:
        return f"{self.processed_posts} out of {self.max_posts}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StageResult:
    stage_name: str
    status: StageStatus
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass
class RuntimeState:
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineRunState:
    status: RunStatus = RunStatus.PENDING
    progress: ProgressState = field(default_factory=ProgressState)
    runtime: RuntimeState = field(default_factory=RuntimeState)
    stage_results: List[StageResult] = field(default_factory=list)
    stop_reason: Optional[str] = None

    def add_stage_result(self, result: StageResult) -> None:
        self.stage_results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "runtime": self.runtime.to_dict(),
            "stage_results": [item.to_dict() for item in self.stage_results],
            "stop_reason": self.stop_reason,
        }


@dataclass
class PipelineOptions:
    max_posts: int = 20
    continue_on_post_error: bool = True
    stop_after_post_errors: Optional[int] = None


@dataclass
class PipelineResult:
    run_state: PipelineRunState
    request_payload: Optional[Dict[str, Any]] = None
    ranked_posts: List[Dict[str, Any]] = field(default_factory=list)
    presented_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_state": self.run_state.to_dict(),
            "request_payload": self.request_payload,
            "ranked_posts": self.ranked_posts,
            "presented_results": self.presented_results,
        }

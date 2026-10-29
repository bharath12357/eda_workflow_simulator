"""Plain data containers for stage results and the final report."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageResult:
    """Outcome of one workflow stage."""

    name: str
    status: str
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0.0
    attempts: int = 0
    messages: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowReport:
    """Everything that happened in one pipeline run (written as JSON)."""

    run_id: str
    tool_version: str
    design_file: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: float
    config: Dict[str, Any]
    stages: List[StageResult]
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["stages"] = [stage.to_dict() for stage in self.stages]
        return data

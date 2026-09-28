from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class VerificationResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class RecoveryDecision(str, Enum):
    RETRY = "retry"
    ALTERNATIVE = "alternative_action"
    REOBSERVE = "re_observe"
    REPLAN = "replan"
    RESTORE = "restore_checkpoint"
    ESCALATE = "human_escalation"
    ABORT = "abort"


@dataclass(slots=True)
class Action:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    requires_approval: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Action":
        return cls(**value)


@dataclass(slots=True)
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class Observation:
    timestamp: str = field(default_factory=utc_now)
    screenshot: str | None = None
    url: str | None = None
    title: str | None = None
    page_text: str = ""
    active_app: str | None = None
    task_status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Verification:
    result: VerificationResult
    reason: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Subtask:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependency: list[str] = field(default_factory=list)
    retry_count: int = 0
    evidence: list[str] = field(default_factory=list)
    error: str | None = None
    action: Action | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Subtask":
        item = dict(value)
        item["status"] = TaskStatus(item.get("status", TaskStatus.PENDING))
        if item.get("action"):
            item["action"] = Action.from_dict(item["action"])
        return cls(**item)


@dataclass(slots=True)
class StepTrace:
    step_id: int
    timestamp: str
    observation: dict[str, Any]
    reasoning_summary: str
    selected_action: str
    action_arguments: dict[str, Any]
    action_result: dict[str, Any]
    verifier_result: dict[str, Any]
    error: str | None
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

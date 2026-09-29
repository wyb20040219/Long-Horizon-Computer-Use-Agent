from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import Observation, Subtask, TaskStatus, utc_now


@dataclass(slots=True)
class AgentState:
    run_id: str
    user_goal: str
    todos: list[Subtask] = field(default_factory=list)
    current_step: int = 0
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    latest_observation: Observation | None = None
    completed_subtasks: list[str] = field(default_factory=list)
    failed_actions: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    important_context: dict[str, Any] = field(default_factory=dict)
    planner_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    status: TaskStatus = TaskStatus.PENDING

    def next_subtask(self) -> Subtask | None:
        done = set(self.completed_subtasks)
        for task in self.todos:
            if task.status == TaskStatus.PENDING and set(task.dependency).issubset(done):
                return task
        return None

    def mark_completed(self, task: Subtask, evidence: list[str]) -> None:
        task.status = TaskStatus.COMPLETED
        task.evidence.extend(evidence)
        if task.id not in self.completed_subtasks:
            self.completed_subtasks.append(task.id)
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentState":
        item = dict(value)
        item["todos"] = [Subtask.from_dict(x) for x in item.get("todos", [])]
        if item.get("latest_observation"):
            item["latest_observation"] = Observation(**item["latest_observation"])
        item["status"] = TaskStatus(item.get("status", TaskStatus.PENDING))
        return cls(**item)

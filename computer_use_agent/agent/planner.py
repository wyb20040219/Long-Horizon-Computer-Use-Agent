from __future__ import annotations

from ..core.models import Action, Subtask, TaskStatus
from ..llm.client import LLMClient
from ..llm.prompts import PLANNER_PROMPT, SYSTEM_PROMPT


class TaskPlanner:
    """A deterministic baseline planner; an LLM planner can replace it."""

    ALLOWED_ACTIONS = {"open_url", "click", "type", "scroll", "back", "refresh", "wait", "assert_text", "mouse_click", "keyboard_input", "hotkey", "screenshot", "read_file", "write_file"}

    def __init__(self, client: LLMClient | None = None):
        self.client = client
        self.last_llm_error: str | None = None

    def plan(self, goal: str, dry_run: bool = False) -> list[Subtask]:
        if not goal.strip():
            raise ValueError("Goal cannot be empty")
        if dry_run:
            return [
                Subtask("observe", "Observe the mock browser", action=Action("open_url", {"url": "https://example.com"})),
                Subtask("extract", "Extract the example page title", dependency=["observe"], action=Action("assert_text", {"text": "Example Domain"})),
                Subtask("save", "Save the verified result", dependency=["extract"], action=Action("write_file", {"path": "artifacts/dry_run_result.txt", "content": "Example Domain\n"})),
            ]
        if self.client:
            try:
                payload = self.client.complete_json(SYSTEM_PROMPT, PLANNER_PROMPT.format(goal=goal, actions=", ".join(sorted(self.ALLOWED_ACTIONS))))
                return self._parse_model_plan(payload)
            except Exception as exc:
                # The model is an optional planning enhancement. A network or
                # schema failure must not make the local agent unusable.
                self.last_llm_error = str(exc)
        # Safe generic baseline: inspect a page if the goal contains a URL, then persist a report.
        words = goal.split()
        url = next((w for w in words if w.startswith(("http://", "https://"))), "https://example.com")
        return [
            Subtask("browse", f"Open source page for: {goal}", action=Action("open_url", {"url": url})),
            Subtask("inspect", "Inspect page content", dependency=["browse"], action=Action("wait", {"seconds": 1})),
            Subtask("report", "Write an execution report", dependency=["inspect"], action=Action("write_file", {"path": "artifacts/result.txt", "content": f"Goal: {goal}\nSource: {url}\n"})),
        ]

    def _parse_model_plan(self, payload: object) -> list[Subtask]:
        if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
            raise ValueError("Model plan must be an object containing a tasks array")
        tasks: list[Subtask] = []
        known: set[str] = set()
        for raw in payload["tasks"]:
            if not isinstance(raw, dict) or not isinstance(raw.get("action"), dict):
                raise ValueError("Each model task must contain an action")
            task = Subtask.from_dict(raw)
            if not task.id or task.id in known:
                raise ValueError("Task IDs must be non-empty and unique")
            if task.action is None or task.action.name not in self.ALLOWED_ACTIONS:
                raise ValueError("Model selected a non-allowlisted action")
            if not set(task.dependency).issubset(known):
                raise ValueError("Dependencies must reference earlier tasks")
            known.add(task.id); tasks.append(task)
        if not tasks:
            raise ValueError("Model plan cannot be empty")
        return tasks

    def replan(self, todos: list[Subtask], failed_id: str) -> list[Subtask]:
        for task in todos:
            if task.id == failed_id:
                task.status = TaskStatus.PENDING
                task.error = None
        return todos

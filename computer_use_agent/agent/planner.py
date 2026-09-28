from __future__ import annotations

from pathlib import Path

from ..core.models import Action, Subtask, TaskStatus


class TaskPlanner:
    """A deterministic baseline planner; an LLM planner can replace it."""

    def plan(self, goal: str, dry_run: bool = False) -> list[Subtask]:
        if not goal.strip():
            raise ValueError("Goal cannot be empty")
        if dry_run:
            return [
                Subtask("observe", "Observe the mock browser", action=Action("open_url", {"url": "https://example.com"})),
                Subtask("extract", "Extract the example page title", dependency=["observe"], action=Action("assert_text", {"text": "Example Domain"})),
                Subtask("save", "Save the verified result", dependency=["extract"], action=Action("write_file", {"path": "artifacts/dry_run_result.txt", "content": "Example Domain\n"})),
            ]
        # Safe generic baseline: inspect a page if the goal contains a URL, then persist a report.
        words = goal.split()
        url = next((w for w in words if w.startswith(("http://", "https://"))), "https://example.com")
        return [
            Subtask("browse", f"Open source page for: {goal}", action=Action("open_url", {"url": url})),
            Subtask("inspect", "Inspect page content", dependency=["browse"], action=Action("wait", {"seconds": 1})),
            Subtask("report", "Write an execution report", dependency=["inspect"], action=Action("write_file", {"path": "artifacts/result.txt", "content": f"Goal: {goal}\nSource: {url}\n"})),
        ]

    def replan(self, todos: list[Subtask], failed_id: str) -> list[Subtask]:
        for task in todos:
            if task.id == failed_id:
                task.status = TaskStatus.PENDING
                task.error = None
        return todos

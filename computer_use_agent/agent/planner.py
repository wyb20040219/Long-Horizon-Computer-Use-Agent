from __future__ import annotations

import re
import time
from typing import Any

from ..core.models import Action, Subtask, TaskStatus
from ..llm.client import LLMClient
from ..llm.prompts import PLANNER_PROMPT, SYSTEM_PROMPT


class PlannerValidationError(ValueError):
    """A safe, internally generated model-plan validation error."""


class TaskPlanner:
    """A deterministic baseline planner; an LLM planner can replace it."""

    ALLOWED_ACTIONS = {"open_url", "click", "type", "scroll", "back", "refresh", "wait", "assert_text", "mouse_click", "keyboard_input", "hotkey", "screenshot", "read_file", "write_file"}
    OUTPUT_PATH_PATTERN = re.compile(r"(?<!\S)[\"']?([^\s\"']+\.(?:txt|md|json|csv))[\"']?", re.IGNORECASE)

    def __init__(self, client: LLMClient | None = None):
        self.client = client
        self.last_llm_error: str | None = None
        self.last_plan_metadata: dict[str, Any] = {}

    def plan(self, goal: str, dry_run: bool = False) -> list[Subtask]:
        if not goal.strip():
            raise ValueError("Goal cannot be empty")
        self.last_llm_error = None
        requested_output = self._extract_output_path(goal)
        if dry_run:
            self.last_plan_metadata = self._metadata("deterministic")
            output_path = requested_output or "artifacts/dry_run_result.txt"
            output_content = "{title}\n\n{page_text}\n" if requested_output else "Example Domain\n"
            return [
                Subtask("observe", "Observe the mock browser", action=Action("open_url", {"url": "https://example.com"})),
                Subtask("extract", "Extract the example page title", dependency=["observe"], action=Action("assert_text", {"text": "Example Domain"})),
                Subtask("save", "Save the verified result", dependency=["extract"], action=Action("write_file", {"path": output_path, "content": output_content})),
            ]
        if self.client:
            started = time.perf_counter()
            try:
                payload = self.client.complete_json(SYSTEM_PROMPT, PLANNER_PROMPT.format(goal=goal, actions=", ".join(sorted(self.ALLOWED_ACTIONS))))
                tasks = self._parse_model_plan(payload)
                self.last_plan_metadata = self._metadata("llm", (time.perf_counter() - started) * 1000)
                return self._preserve_requested_output(tasks, requested_output)
            except Exception as exc:
                # The model is an optional planning enhancement. A network or
                # schema failure must not make the local agent unusable.
                summary = self._safe_exception_summary(exc)
                self.last_llm_error = summary
                self.last_plan_metadata = self._metadata(
                    "deterministic_fallback",
                    (time.perf_counter() - started) * 1000,
                    fallback_reason="llm_call_or_plan_validation_failed",
                    exception_type=type(exc).__name__,
                    exception_summary=summary,
                )
        else:
            self.last_plan_metadata = self._metadata("deterministic")
        # Safe generic baseline: inspect a page if the goal contains a URL, then persist a report.
        words = goal.split()
        url = next((w for w in words if w.startswith(("http://", "https://"))), "https://example.com")
        output_path = requested_output or "artifacts/result.txt"
        return [
            Subtask("browse", f"Open source page for: {goal}", action=Action("open_url", {"url": url})),
            Subtask("inspect", "Inspect page content", dependency=["browse"], action=Action("wait", {"seconds": 1})),
            Subtask("report", "Write the observed page title and main text", dependency=["inspect"], action=Action("write_file", {"path": output_path, "content": "{title}\n\n{page_text}\n"})),
        ]

    def _metadata(self, backend: str, latency_ms: float | None = None, **extra: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "planner_backend": backend,
            "llm_latency_ms": round(latency_ms, 3) if latency_ms is not None else None,
        }
        if self.client is not None and backend != "deterministic":
            model = getattr(self.client, "model", None)
            if model:
                metadata["model"] = str(model)
        metadata.update(extra)
        return metadata

    def _safe_exception_summary(self, exc: Exception) -> str:
        if isinstance(exc, PlannerValidationError):
            return " ".join(str(exc).split())[:500]
        return "LLM request failed; exception details [REDACTED]"

    @classmethod
    def _extract_output_path(cls, goal: str) -> str | None:
        matches = [match for match in cls.OUTPUT_PATH_PATTERN.findall(goal) if not match.lower().startswith(("http://", "https://"))]
        return matches[-1] if matches else None

    @staticmethod
    def _preserve_requested_output(tasks: list[Subtask], requested_output: str | None) -> list[Subtask]:
        if requested_output is None:
            return tasks
        writes = [task for task in tasks if task.action and task.action.name == "write_file"]
        if not writes:
            raise PlannerValidationError("Model plan omitted the explicitly requested output file")
        writes[-1].action.arguments["path"] = requested_output
        return tasks

    def _parse_model_plan(self, payload: object) -> list[Subtask]:
        if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
            raise PlannerValidationError("Model plan must be an object containing a tasks array")
        tasks: list[Subtask] = []
        known: set[str] = set()
        for raw in payload["tasks"]:
            if not isinstance(raw, dict) or not isinstance(raw.get("action"), dict):
                raise PlannerValidationError("Each model task must contain an action")
            task = Subtask.from_dict(raw)
            if not task.id or task.id in known:
                raise PlannerValidationError("Task IDs must be non-empty and unique")
            if task.action is None or task.action.name not in self.ALLOWED_ACTIONS:
                raise PlannerValidationError("Model selected a non-allowlisted action")
            if not set(task.dependency).issubset(known):
                raise PlannerValidationError("Dependencies must reference earlier tasks")
            known.add(task.id); tasks.append(task)
        if not tasks:
            raise PlannerValidationError("Model plan cannot be empty")
        return tasks

    def replan(self, todos: list[Subtask], failed_id: str) -> list[Subtask]:
        for task in todos:
            if task.id == failed_id:
                task.status = TaskStatus.PENDING
                task.error = None
        return todos

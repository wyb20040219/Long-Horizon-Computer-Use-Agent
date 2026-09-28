from __future__ import annotations

import time
import uuid
import json
import os
from dataclasses import asdict
from typing import Callable

from ..core.checkpoint import CheckpointStore
from ..core.config import AgentConfig
from ..core.models import Action, StepTrace, TaskStatus, VerificationResult, utc_now
from ..core.state import AgentState
from ..core.trace import TraceWriter
from ..tools.browser import BrowserController
from ..tools.desktop import DesktopController
from ..tools.filesystem import FileSystemController
from ..tools.registry import ActionRegistry
from .context_manager import ContextManager
from .planner import TaskPlanner
from .recovery import RecoveryPolicy
from .verifier import Verifier
from ..llm.client import OpenAICompatibleClient


class AgentRuntime:
    def __init__(self, config: AgentConfig, approval_handler: Callable[[Action], bool] | None = None, planner: TaskPlanner | None = None):
        self.config = config
        self.store = CheckpointStore(config.runs_dir)
        if planner is not None:
            self.planner = planner
        elif os.getenv("OPENAI_API_KEY") and not config.dry_run:
            self.planner = TaskPlanner(OpenAICompatibleClient())
        else:
            self.planner = TaskPlanner()
        self.verifier = Verifier()
        self.recovery = RecoveryPolicy(config.max_retries)
        self.context = ContextManager()
        self.approval_handler = approval_handler or self._approve
        self.browser: BrowserController | None = None

    def _approve(self, action: Action) -> bool:
        if self.config.auto_approve: return True
        choice = input(f"Approve {action.name} {action.arguments}? [approve/reject/modify]: ").strip().lower()
        if choice == "modify":
            try:
                changed = json.loads(input("New action arguments as JSON object: "))
                if not isinstance(changed, dict): raise ValueError("arguments must be an object")
                action.arguments = changed
                return input(f"Approve modified {action.name} {changed}? [y/N]: ").strip().lower() in {"yes", "y"}
            except (ValueError, json.JSONDecodeError) as exc:
                print(f"Invalid modification: {exc}")
                return False
        return choice in {"approve", "a", "yes", "y"}

    def _registry(self, run_id: str) -> ActionRegistry:
        run_dir = self.store.run_dir(run_id)
        self.browser = BrowserController(self.config.allowed_domains, run_dir / "screenshots", mock=self.config.dry_run, headless=self.config.headless, failure_budget=self.config.mock_failures)
        return ActionRegistry(self.browser, DesktopController(run_dir / "screenshots"), FileSystemController(self.config.workspace, self.config.protected_paths))

    def new_state(self, goal: str) -> AgentState:
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        return AgentState(run_id=run_id, user_goal=goal, todos=self.planner.plan(goal, self.config.dry_run), status=TaskStatus.IN_PROGRESS)

    def run(self, goal: str | None = None, resume_id: str | None = None) -> AgentState:
        if bool(goal) == bool(resume_id):
            raise ValueError("Provide exactly one of goal or resume_id")
        state = self.store.load(resume_id) if resume_id else self.new_state(goal or "")
        state.status = TaskStatus.IN_PROGRESS
        registry = self._registry(state.run_id)
        if resume_id and state.latest_observation and state.latest_observation.url and state.latest_observation.url.startswith(("http://", "https://")):
            registry.execute(Action("open_url", {"url": state.latest_observation.url}, "Restore browser checkpoint"), lambda _: True)
        trace_writer = TraceWriter(self.store.run_dir(state.run_id) / "trace.jsonl")
        started = time.monotonic()
        self.store.save(state)
        try:
            while state.current_step < self.config.max_steps:
                if time.monotonic() - started > self.config.timeout_seconds:
                    state.status = TaskStatus.BLOCKED; state.important_context["stop_reason"] = "timeout"; break
                task = state.next_subtask()
                if task is None: break
                task.status = TaskStatus.IN_PROGRESS
                action = task.action
                if action is None:
                    task.status = TaskStatus.FAILED; task.error = "Planner emitted no action"; break
                before = time.monotonic()
                observation = self.browser.observe() if self.browser else None
                state.latest_observation = observation
                _ = self.context.build(state)
                result = registry.execute(action, self.approval_handler)
                after_observation = self.browser.observe() if self.browser else observation
                state.latest_observation = after_observation
                verification = self.verifier.verify_subtask(self.verifier.verify_action(action, result, after_observation))
                state.current_step += 1
                error = result.error
                if verification.result == VerificationResult.PASS:
                    state.mark_completed(task, verification.evidence)
                    state.retry_count = 0
                else:
                    task.retry_count += 1; state.retry_count += 1; task.error = error or verification.reason
                    state.failed_actions.append({"step": state.current_step, "task": task.id, "action": action.name, "error": task.error})
                    decision = self.recovery.decide(task.retry_count - 1, rejected=bool(result.data.get("rejected")))
                    state.important_context["last_recovery"] = decision.value
                    if decision.value == "retry": task.status = TaskStatus.PENDING
                    elif decision.value == "replan": self.planner.replan(state.todos, task.id)
                    else: task.status = TaskStatus.BLOCKED; state.status = TaskStatus.BLOCKED
                record = StepTrace(state.current_step, utc_now(), asdict(observation) if observation else {}, f"Execute subtask {task.id}: {task.description}", action.name, action.arguments, asdict(result), asdict(verification), error, (time.monotonic() - before) * 1000)
                trace_writer.append(record); state.execution_history.append(record.to_dict())
                if state.current_step % self.config.checkpoint_every == 0: self.store.save(state)
                if state.status == TaskStatus.BLOCKED: break
            final = self.verifier.verify_goal(len(state.completed_subtasks), len(state.todos))
            if final.result == VerificationResult.PASS: state.status = TaskStatus.COMPLETED
            elif state.status != TaskStatus.BLOCKED: state.status = TaskStatus.FAILED
            state.important_context["final_verification"] = asdict(final)
            self.store.save(state)
            return state
        finally:
            if self.browser: self.browser.close()

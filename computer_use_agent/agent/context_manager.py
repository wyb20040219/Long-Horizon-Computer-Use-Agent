from __future__ import annotations

from typing import Any

from ..core.state import AgentState


class ContextManager:
    def __init__(self, recent_limit: int = 6, max_chars: int = 12000):
        self.recent_limit, self.max_chars = recent_limit, max_chars

    def build(self, state: AgentState) -> dict[str, Any]:
        older = state.execution_history[:-self.recent_limit]
        recent = state.execution_history[-self.recent_limit:]
        compressed = "; ".join(f"step {x.get('step_id')}: {x.get('selected_action')} -> {x.get('verifier_result', {}).get('result')}" for x in older)
        context = {
            "user_goal": state.user_goal,
            "task_plan": [{"id": t.id, "description": t.description, "status": t.status.value} for t in state.todos],
            "recent_steps": recent,
            "compressed_history": compressed,
            "important_facts": state.important_context,
            "current_observation": state.latest_observation.__dict__ if hasattr(state.latest_observation, "__dict__") else (str(state.latest_observation) if state.latest_observation else None),
        }
        # Bound large textual observations without losing structured plan/state.
        if len(str(context)) > self.max_chars:
            context["recent_steps"] = recent[-2:]
            context["compressed_history"] = compressed[-2000:]
        return context

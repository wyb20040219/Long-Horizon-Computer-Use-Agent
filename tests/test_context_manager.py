from computer_use_agent.agent.context_manager import ContextManager
from computer_use_agent.core.models import Observation
from computer_use_agent.core.state import AgentState


def test_context_trims_old_history_and_keeps_goal():
    state = AgentState("run-context", "important goal")
    state.execution_history = [{"step_id": i, "selected_action": "wait", "verifier_result": {"result": "PASS"}} for i in range(10)]
    state.latest_observation = Observation(page_text="visible")
    context = ContextManager(recent_limit=3).build(state)
    assert context["user_goal"] == "important goal"
    assert len(context["recent_steps"]) == 3
    assert "step 0" in context["compressed_history"]
    assert context["current_observation"]["page_text"] == "visible"

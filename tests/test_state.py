from computer_use_agent.core.models import Action, Subtask, TaskStatus
from computer_use_agent.core.state import AgentState


def test_dependencies_control_next_subtask():
    state = AgentState("run-test", "goal", [Subtask("a", "first", action=Action("wait")), Subtask("b", "second", dependency=["a"], action=Action("wait"))])
    assert state.next_subtask().id == "a"
    state.mark_completed(state.todos[0], ["ok"])
    assert state.next_subtask().id == "b"
    assert state.todos[0].status == TaskStatus.COMPLETED


def test_state_round_trip_preserves_enums_and_actions():
    original = AgentState("run-safe", "goal", [Subtask("a", "first", action=Action("wait", {"seconds": 1}))])
    restored = AgentState.from_dict(original.to_dict())
    assert restored.todos[0].status == TaskStatus.PENDING
    assert restored.todos[0].action.arguments == {"seconds": 1}

import pytest

from computer_use_agent.agent.planner import TaskPlanner


def test_dry_run_plan_has_dependencies_and_actions():
    plan = TaskPlanner().plan("demo", dry_run=True)
    assert [task.id for task in plan] == ["observe", "extract", "save"]
    assert plan[1].dependency == ["observe"]
    assert all(task.action for task in plan)


def test_empty_goal_is_rejected():
    with pytest.raises(ValueError):
        TaskPlanner().plan("  ")


class FakeClient:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, prompt): return self.payload


def test_llm_plan_is_validated_and_used():
    payload = {"tasks": [{"id": "one", "description": "open", "dependency": [], "action": {"name": "open_url", "arguments": {"url": "https://example.com"}}}]}
    plan = TaskPlanner(FakeClient(payload)).plan("visit")
    assert plan[0].action.name == "open_url"


def test_unsafe_llm_plan_falls_back_without_executing_it():
    payload = {"tasks": [{"id": "one", "description": "unsafe", "dependency": [], "action": {"name": "shell", "arguments": {"command": "bad"}}}]}
    planner = TaskPlanner(FakeClient(payload))
    plan = planner.plan("do something")
    assert all(task.action.name != "shell" for task in plan)
    assert "non-allowlisted" in planner.last_llm_error

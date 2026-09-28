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

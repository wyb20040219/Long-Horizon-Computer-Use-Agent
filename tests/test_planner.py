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
    model = "test-model"

    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, prompt): return self.payload


def test_llm_plan_is_validated_and_used():
    payload = {"tasks": [{"id": "one", "description": "open", "dependency": [], "action": {"name": "open_url", "arguments": {"url": "https://example.com"}}}]}
    plan = TaskPlanner(FakeClient(payload)).plan("visit")
    assert plan[0].action.name == "open_url"
    assert planner_metadata_for(FakeClient(payload), "visit")["planner_backend"] == "llm"


def planner_metadata_for(client, goal):
    planner = TaskPlanner(client)
    planner.plan(goal)
    return planner.last_plan_metadata


def test_unsafe_llm_plan_falls_back_without_executing_it():
    payload = {"tasks": [{"id": "one", "description": "unsafe", "dependency": [], "action": {"name": "shell", "arguments": {"command": "bad"}}}]}
    planner = TaskPlanner(FakeClient(payload))
    plan = planner.plan("do something")
    assert all(task.action.name != "shell" for task in plan)
    assert "non-allowlisted" in planner.last_llm_error


def test_deterministic_plan_preserves_requested_output_path():
    plan = TaskPlanner().plan("Open https://example.com and save it into workspace/custom-report.txt")
    report = next(task for task in plan if task.action.name == "write_file")
    assert report.action.arguments["path"] == "workspace/custom-report.txt"
    assert "{title}" in report.action.arguments["content"]
    assert "{page_text}" in report.action.arguments["content"]


def test_llm_plan_cannot_replace_explicit_output_path():
    payload = {"tasks": [{"id": "save", "description": "save", "dependency": [], "action": {"name": "write_file", "arguments": {"path": "artifacts/wrong.txt", "content": "ok"}}}]}
    plan = TaskPlanner(FakeClient(payload)).plan("Save result to workspace/requested.txt")
    assert plan[0].action.arguments["path"] == "workspace/requested.txt"


def test_source_url_ending_in_txt_is_not_mistaken_for_output_path():
    plan = TaskPlanner().plan("Open https://example.com/source.txt and inspect it")
    report = next(task for task in plan if task.action.name == "write_file")
    assert report.action.arguments["path"] == "artifacts/result.txt"


def test_deterministic_backend_metadata():
    planner = TaskPlanner()
    planner.plan("inspect example")
    assert planner.last_plan_metadata == {"planner_backend": "deterministic", "llm_latency_ms": None}


def test_llm_backend_records_model_and_latency():
    payload = {"tasks": [{"id": "one", "description": "wait", "dependency": [], "action": {"name": "wait", "arguments": {"seconds": 0}}}]}
    metadata = planner_metadata_for(FakeClient(payload), "wait")
    assert metadata["planner_backend"] == "llm"
    assert metadata["model"] == "test-model"
    assert metadata["llm_latency_ms"] >= 0


class FailingClient:
    model = "failing-model"
    api_key = "sk-super-secret-value"

    def complete_json(self, system, prompt):
        raise RuntimeError("request failed api_key=sk-super-secret-value bearer sk-another-secret")


def test_llm_fallback_metadata_is_sanitized():
    planner = TaskPlanner(FailingClient())
    plan = planner.plan("inspect example")
    metadata = planner.last_plan_metadata
    serialized = str(metadata)
    assert plan
    assert metadata["planner_backend"] == "deterministic_fallback"
    assert metadata["model"] == "failing-model"
    assert metadata["fallback_reason"] == "llm_call_or_plan_validation_failed"
    assert metadata["exception_type"] == "RuntimeError"
    assert "[REDACTED]" in metadata["exception_summary"]
    assert "super-secret" not in serialized
    assert "another-secret" not in serialized

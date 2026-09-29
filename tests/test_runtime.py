import json

from computer_use_agent.agent.runtime import AgentRuntime
from computer_use_agent.agent.planner import TaskPlanner
from computer_use_agent.core.config import AgentConfig
from computer_use_agent.core.models import TaskStatus


def test_dry_run_creates_trace_checkpoint_and_output(tmp_path):
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True)
    state = AgentRuntime(config).run(goal="demo")
    run_dir = tmp_path / "runs" / state.run_id
    assert state.status == TaskStatus.COMPLETED
    assert state.current_step == 3
    assert (run_dir / "state.json").exists()
    assert len((run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    assert (tmp_path / "artifacts" / "dry_run_result.txt").read_text() == "Example Domain\n"
    saved_state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    trace = json.loads((run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert saved_state["important_context"]["final_verification"]["result"] == "PASS"
    assert saved_state["planner_metadata"]["planner_backend"] == "deterministic"
    assert trace["planner_metadata"]["planner_backend"] == "deterministic"


def test_resume_completed_run_is_idempotent(tmp_path):
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True)
    runtime = AgentRuntime(config)
    first = runtime.run(goal="demo")
    resumed = AgentRuntime(config).run(resume_id=first.run_id)
    assert resumed.status == TaskStatus.COMPLETED
    assert resumed.current_step == 3


def test_runtime_recovers_from_one_transient_failure(tmp_path):
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True, mock_failures={"open_url": 1})
    state = AgentRuntime(config).run(goal="recover")
    assert state.status == TaskStatus.COMPLETED
    assert state.current_step == 4
    assert state.todos[0].retry_count == 1
    assert len(state.failed_actions) == 1


def test_runtime_writes_observed_title_and_main_text_to_requested_path(tmp_path):
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True)
    state = AgentRuntime(config).run(goal="Open https://example.com and save it into workspace/report.txt")
    output = (tmp_path / "workspace" / "report.txt").read_text(encoding="utf-8")
    assert state.status == TaskStatus.COMPLETED
    assert "Example Domain" in output
    assert "illustrative examples" in output


def test_runtime_notifies_planner_backend_before_execution(tmp_path):
    events = []
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True)
    AgentRuntime(config, planner_observer=events.append).run(goal="demo")
    assert events == [{"planner_backend": "deterministic", "llm_latency_ms": None}]


class SecretFailingClient:
    model = "fallback-model"
    api_key = "sk-never-persist-this"

    def complete_json(self, system, prompt):
        raise ConnectionError("failed with sk-never-persist-this")


class MockBrowserFallbackPlanner(TaskPlanner):
    def plan(self, goal, dry_run=False):
        return super().plan(goal, dry_run=False)


def test_fallback_observability_is_persisted_without_secrets(tmp_path):
    config = AgentConfig(workspace=tmp_path, dry_run=True, auto_approve=True)
    planner = MockBrowserFallbackPlanner(SecretFailingClient())
    state = AgentRuntime(config, planner=planner).run(goal="inspect example")
    run_dir = tmp_path / "runs" / state.run_id
    state_text = (run_dir / "state.json").read_text(encoding="utf-8")
    trace_text = (run_dir / "trace.jsonl").read_text(encoding="utf-8")
    saved = json.loads(state_text)
    assert saved["planner_metadata"]["planner_backend"] == "deterministic_fallback"
    assert saved["planner_metadata"]["model"] == "fallback-model"
    assert saved["planner_metadata"]["fallback_reason"] == "llm_call_or_plan_validation_failed"
    assert saved["planner_metadata"]["llm_latency_ms"] >= 0
    assert '"planner_backend": "deterministic_fallback"' in trace_text
    assert "sk-never-persist-this" not in state_text + trace_text

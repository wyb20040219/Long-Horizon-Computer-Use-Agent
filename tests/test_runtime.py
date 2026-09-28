import json

from computer_use_agent.agent.runtime import AgentRuntime
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
    assert json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["important_context"]["final_verification"]["result"] == "PASS"


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

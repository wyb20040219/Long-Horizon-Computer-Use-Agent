import os

from computer_use_agent.agent.planner import TaskPlanner
from computer_use_agent.agent.runtime import AgentRuntime
from computer_use_agent.core.config import AgentConfig, load_project_environment, project_root
from computer_use_agent.llm.client import OpenAICompatibleClient


def test_project_root_is_derived_from_config_module():
    assert (project_root() / "main.py").is_file()
    assert (project_root() / "computer_use_agent").is_dir()


def test_missing_dotenv_is_allowed(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert load_project_environment(tmp_path) is False
    assert "OPENAI_API_KEY" not in os.environ


def test_dotenv_loads_values_without_overriding_os_environment(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=dotenv-test-key\n"
        "OPENAI_BASE_URL=https://dotenv.invalid/v1\n"
        "OPENAI_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_MODEL", "os-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert load_project_environment(tmp_path) is True
    assert os.environ["OPENAI_API_KEY"] == "dotenv-test-key"
    assert os.environ["OPENAI_BASE_URL"] == "https://dotenv.invalid/v1"
    assert os.environ["OPENAI_MODEL"] == "os-model"


def test_loaded_dotenv_selects_llm_planner_for_live_run(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=selection-test-key\nOPENAI_MODEL=selection-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    load_project_environment(tmp_path)
    runtime = AgentRuntime(AgentConfig(workspace=tmp_path, dry_run=False))
    assert isinstance(runtime.planner, TaskPlanner)
    assert isinstance(runtime.planner.client, OpenAICompatibleClient)
    assert runtime.planner.client.model == "selection-model"


def test_dry_run_remains_deterministic_with_loaded_api_key(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=selection-test-key\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    load_project_environment(tmp_path)
    runtime = AgentRuntime(AgentConfig(workspace=tmp_path, dry_run=True))
    state = runtime.new_state("demo")
    assert runtime.planner.client is None
    assert state.planner_metadata["planner_backend"] == "deterministic"

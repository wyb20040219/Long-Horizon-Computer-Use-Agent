import json

import pytest

from computer_use_agent.core.checkpoint import CheckpointStore
from computer_use_agent.core.state import AgentState


def test_checkpoint_save_and_load(tmp_path):
    store = CheckpointStore(tmp_path)
    state = AgentState("run-valid_1", "persist me")
    path = store.save(state)
    assert json.loads(path.read_text(encoding="utf-8"))["user_goal"] == "persist me"
    assert store.load(state.run_id).user_goal == "persist me"
    assert (tmp_path / state.run_id / "checkpoints" / "step-0000.json").exists()


def test_checkpoint_rejects_path_traversal(tmp_path):
    store = CheckpointStore(tmp_path)
    with pytest.raises(ValueError):
        store.load("../escape")

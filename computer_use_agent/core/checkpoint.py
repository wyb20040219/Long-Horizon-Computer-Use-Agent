from __future__ import annotations

import json
import os
from pathlib import Path

from .state import AgentState


class CheckpointStore:
    def __init__(self, runs_dir: Path):
        self.runs_dir = runs_dir

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
            raise ValueError("Invalid run_id")
        return self.runs_dir / run_id

    def save(self, state: AgentState) -> Path:
        directory = self.run_dir(state.run_id)
        checkpoint_dir = directory / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        target = directory / "state.json"
        temporary = directory / "state.json.tmp"
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, target)
        numbered = checkpoint_dir / f"step-{state.current_step:04d}.json"
        numbered.write_text(payload, encoding="utf-8")
        return target

    def load(self, run_id: str) -> AgentState:
        path = self.run_dir(run_id) / "state.json"
        if not path.exists():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return AgentState.from_dict(json.loads(path.read_text(encoding="utf-8")))

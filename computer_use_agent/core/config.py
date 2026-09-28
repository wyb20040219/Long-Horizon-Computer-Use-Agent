from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AgentConfig:
    workspace: Path = field(default_factory=lambda: Path.cwd().resolve())
    runs_dir: Path = field(default_factory=lambda: Path("runs"))
    max_steps: int = 30
    max_retries: int = 2
    timeout_seconds: int = 300
    allowed_domains: tuple[str, ...] = ("example.com", "httpbin.org")
    protected_paths: tuple[str, ...] = ()
    headless: bool = True
    dry_run: bool = False
    auto_approve: bool = False
    checkpoint_every: int = 1
    mock_failures: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        self.runs_dir = (self.workspace / self.runs_dir).resolve() if not self.runs_dir.is_absolute() else self.runs_dir.resolve()
        if not self.protected_paths:
            self.protected_paths = (str(Path.home().resolve()), str(Path("C:/Windows").resolve()))

    @classmethod
    def from_env(cls, **overrides: object) -> "AgentConfig":
        values: dict[str, object] = {
            "max_steps": int(os.getenv("AGENT_MAX_STEPS", "30")),
            "max_retries": int(os.getenv("AGENT_MAX_RETRIES", "2")),
            "timeout_seconds": int(os.getenv("AGENT_TIMEOUT", "300")),
            "allowed_domains": tuple(filter(None, os.getenv("AGENT_ALLOWED_DOMAINS", "example.com,httpbin.org").split(","))),
        }
        values.update(overrides)
        return cls(**values)

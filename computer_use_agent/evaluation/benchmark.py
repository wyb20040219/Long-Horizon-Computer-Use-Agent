from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from ..agent.runtime import AgentRuntime
from ..core.config import AgentConfig
from ..core.models import TaskStatus


def run_benchmark(tasks_path: Path, results_path: Path, workspace: Path) -> dict[str, Any]:
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    results = []
    for task in tasks:
        config = AgentConfig(workspace=workspace, dry_run=True, auto_approve=True)
        start = time.monotonic(); state = AgentRuntime(config).run(goal=task["goal"]); elapsed = time.monotonic() - start
        results.append({"id": task["id"], "success": state.status == TaskStatus.COMPLETED, "steps": state.current_step, "recovery_count": sum(1 for x in state.execution_history if x.get("error")), "retry_count": state.retry_count, "execution_time_seconds": elapsed})
    summary = {"task_count": len(results), "task_success_rate": sum(x["success"] for x in results) / len(results), "average_steps": statistics.mean(x["steps"] for x in results), "recovery_count": sum(x["recovery_count"] for x in results), "retry_count": sum(x["retry_count"] for x in results), "execution_time_seconds": sum(x["execution_time_seconds"] for x in results)}
    payload = {"summary": summary, "tasks": results}
    results_path.parent.mkdir(parents=True, exist_ok=True); results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

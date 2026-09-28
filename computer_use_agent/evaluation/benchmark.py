from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from ..agent.runtime import AgentRuntime
from ..core.config import AgentConfig
from ..core.models import Observation, TaskStatus


def run_benchmark(tasks_path: Path, results_path: Path, workspace: Path) -> dict[str, Any]:
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    results = []
    for task in tasks:
        scenario = task.get("scenario", "standard")
        failures = {"open_url": 1} if scenario == "transient_failure" else {}
        config = AgentConfig(workspace=workspace, dry_run=True, auto_approve=True, mock_failures=failures)
        runtime = AgentRuntime(config)
        resume_id = None
        if scenario == "resume":
            interrupted = runtime.new_state(task["goal"])
            for completed_task in interrupted.todos[:2]:
                interrupted.mark_completed(completed_task, ["simulated pre-interruption evidence"])
            interrupted.current_step = 2
            interrupted.latest_observation = Observation(url="https://example.com", title="Example Domain", page_text="Example Domain")
            runtime.store.save(interrupted)
            resume_id = interrupted.run_id
        start = time.monotonic()
        state = runtime.run(resume_id=resume_id) if resume_id else runtime.run(goal=task["goal"])
        elapsed = time.monotonic() - start
        recovery_count = sum(1 for x in state.execution_history if x.get("error"))
        results.append({"id": task["id"], "scenario": scenario, "success": state.status == TaskStatus.COMPLETED, "steps": state.current_step, "recovery_count": recovery_count, "retry_count": sum(item.retry_count for item in state.todos), "execution_time_seconds": elapsed, "resumed": resume_id is not None})
    summary = {"task_count": len(results), "task_success_rate": sum(x["success"] for x in results) / len(results), "average_steps": statistics.mean(x["steps"] for x in results), "recovery_count": sum(x["recovery_count"] for x in results), "retry_count": sum(x["retry_count"] for x in results), "execution_time_seconds": sum(x["execution_time_seconds"] for x in results)}
    payload = {"summary": summary, "tasks": results}
    results_path.parent.mkdir(parents=True, exist_ok=True); results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

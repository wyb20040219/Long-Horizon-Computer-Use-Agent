from __future__ import annotations

import argparse
import json
from pathlib import Path

from computer_use_agent.agent.runtime import AgentRuntime
from computer_use_agent.core.config import AgentConfig, load_project_environment
from computer_use_agent.evaluation.benchmark import run_benchmark


def print_planner_metadata(metadata: dict[str, object]) -> None:
    print(f"Planner backend: {metadata.get('planner_backend', 'unknown')}")
    if metadata.get("model"):
        print(f"Model: {metadata['model']}")
    if metadata.get("llm_latency_ms") is not None:
        print(f"LLM latency: {metadata['llm_latency_ms']} ms")
    if metadata.get("fallback_reason"):
        print(f"Fallback reason: {metadata['fallback_reason']}")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Reliable long-horizon computer-use agent")
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Natural-language goal")
    group.add_argument("--resume", metavar="RUN_ID", help="Resume a saved run")
    group.add_argument("--dry-run", action="store_true", help="Run deterministic browser-to-file demo")
    group.add_argument("--benchmark", action="store_true", help="Run five offline benchmark tasks")
    value.add_argument("--headed", action="store_true", help="Show the Playwright browser")
    value.add_argument("--auto-approve", action="store_true", help="Approve guarded actions (trusted demos only)")
    return value


def main() -> int:
    load_project_environment()
    args = parser().parse_args(); workspace = Path.cwd().resolve()
    if args.benchmark:
        output = run_benchmark(workspace / "computer_use_agent/evaluation/tasks.json", workspace / "evaluation/results.json", workspace)
        print(json.dumps(output["summary"], indent=2)); return 0
    config = AgentConfig.from_env(workspace=workspace, dry_run=args.dry_run, headless=not args.headed, auto_approve=args.auto_approve)
    state = AgentRuntime(config, planner_observer=print_planner_metadata).run(goal="Dry-run: verify Example Domain and save the result" if args.dry_run else args.task, resume_id=args.resume)
    print(json.dumps({"run_id": state.run_id, "status": state.status.value, "steps": state.current_step, "completed": state.completed_subtasks, "run_dir": str(config.runs_dir / state.run_id)}, ensure_ascii=False, indent=2))
    return 0 if state.status.value == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

import json

from computer_use_agent.evaluation.benchmark import run_benchmark


def test_benchmark_exercises_recovery_and_resume(tmp_path):
    tasks = [
        {"id": "recover", "scenario": "transient_failure", "goal": "recover"},
        {"id": "resume", "scenario": "resume", "goal": "resume"},
    ]
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
    payload = run_benchmark(tasks_path, tmp_path / "results.json", tmp_path)
    by_id = {item["id"]: item for item in payload["tasks"]}
    assert by_id["recover"]["recovery_count"] == 1
    assert by_id["recover"]["steps"] == 4
    assert by_id["resume"]["resumed"] is True
    assert payload["summary"]["task_success_rate"] == 1.0

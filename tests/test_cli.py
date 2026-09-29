from main import parser, print_planner_metadata


def test_cli_prints_backend_model_and_latency_without_api_key(capsys):
    print_planner_metadata({
        "planner_backend": "llm",
        "model": "test-model",
        "llm_latency_ms": 12.5,
        "api_key": "sk-must-never-print",
    })
    output = capsys.readouterr().out
    assert "Planner backend: llm" in output
    assert "Model: test-model" in output
    assert "LLM latency: 12.5 ms" in output
    assert "sk-must-never-print" not in output

def test_cli_parses_max_steps():
    args = parser().parse_args([
        "--dry-run",
        "--max-steps",
        "2",
    ])

    assert args.max_steps == 2
    assert args.dry_run is True


def test_cli_max_steps_is_none_when_omitted():
    args = parser().parse_args([
        "--dry-run",
    ])

    assert args.max_steps is None
from __future__ import annotations

from fde_lab.cli import main
from fde_lab.story import format_story, run_story

_ORDER = [
    "authentication_401",
    "authorization_403",
    "missing_permission",
    "invalid_configuration",
    "schema_mismatch",
    "malformed_payload",
    "timeout",
    "duplicate_request",
    "dependency_failure",
    "configuration_drift",
]


def test_field_story_runs_the_flow_and_the_ten_failures() -> None:
    report = run_story()
    failed = [
        item.scenario_id + " expected " + item.expected_code + " actual " + item.actual_code
        for item in report.incidents
        if not item.passed
    ]
    assert report.contract_findings == []
    assert failed == []
    assert report.failed == 0
    assert report.tokens == 0
    assert report.hosted_llm == "not-run"
    assert [item.scenario_id for item in report.incidents] == _ORDER
    assert report.happy_path.passed
    assert report.happy_path.external_calls == 1
    assert report.happy_path.nodes[report.happy_path.nodes.index("validate_input") :] == [
        "validate_input",
        "read_worker",
        "read_balance",
        "reserve_coverage",
        "submit_business_process",
    ]
    assert report.lifecycle.passed
    assert report.lifecycle.backlog_id == "FDE-BACKLOG-001"
    assert "prompt_tool_missing" in report.lifecycle.before_codes
    assert "lab-token-" not in report.model_dump_json()
    by_id = {item.scenario_id: item for item in report.incidents}
    assert by_id["authentication_401"].telemetry.endswith("asor_http=401")
    assert "asor_registered=201" in by_id["authentication_401"].validation
    assert "events=1" in by_id["duplicate_request"].validation
    assert "external_calls=1" in by_id["duplicate_request"].validation
    assert "retry_attempts=3" in by_id["dependency_failure"].validation
    assert "read=ok write=not_in_available_to" in by_id["missing_permission"].validation
    text = format_story(report)
    for label in (
        "Symptom",
        "Telemetry",
        "Diagnosis",
        "Root cause",
        "Fix",
        "Validation",
        "Prevention",
    ):
        assert label in text
    assert "No model is called." in text


def test_run_story_command_exits_zero() -> None:
    assert main(["run-story"]) == 0

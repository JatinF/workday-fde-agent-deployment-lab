from __future__ import annotations

from fastapi.testclient import TestClient

from fde_lab.api import create_app
from fde_lab.cli import main
from fde_lab.load import load_package
from fde_lab.runtime import Runtime
from fde_lab.suite import run_suite


def test_suite_matches_every_expected_case() -> None:
    report = run_suite()
    assert report.failed == 0
    assert report.token_leak_count == 0
    assert report.business_process_events_after_replay == 1
    assert report.external_calls_after_replay == 1
    assert report.gates["development-tenant"] == "not-run"
    assert report.gates["asor-live-post"] == "not-run"
    assert report.gates["hosted-llm"] == "not-run"
    assert report.case_count == len(report.results)
    assert {row.case_id for row in report.results} >= {
        "tenant-not-deployed",
        "asor-400",
        "asor-401",
        "asor-403",
        "asor-404",
        "prompt-wid-missing",
        "prompt-tool-fix",
        "rest-403",
        "soap-401",
        "timeout",
        "retry-then-success",
        "secret-redacted",
    }


def test_api_invoke_preflight_and_asor_stand_in() -> None:
    runtime = Runtime(load_package())
    client = TestClient(create_app(runtime))
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["hosted_llm"] == "not-run"
    assert health.json()["tokens"] == 0
    preflight = client.post("/preflight")
    assert preflight.status_code == 200
    assert preflight.json()["ok"] is True
    missing = client.get("/traces/tr-missing")
    assert missing.status_code == 404
    invoked = client.post(
        "/invoke",
        json={
            "actor_id": "SYN-USER-NOOR",
            "skill": "read-balance",
            "arguments": {"worker_id": "SYN-USER-IVAN"},
        },
    )
    assert invoked.status_code == 200
    body = invoked.json()
    assert body["failure_class"] == "ok"
    assert "lab-token-" not in invoked.text
    fetched = client.get("/traces/" + body["trace_id"])
    assert fetched.status_code == 200
    token = runtime.tokens.issue("SYN-USER-NOOR", 1, valid=True)
    headers = {
        "Authorization": "Bearer " + token.secret,
        "x-lab-domains": "Development",
        "wd-agent-tenant-alias": "SYN-ORG-NORTHLINE",
    }
    rejected = client.post("/asor/agentDefinition", json={}, headers=headers)
    assert rejected.status_code == 400
    created = client.post(
        "/asor/agentDefinition",
        json={
            "name": "time-off-coverage",
            "description": "Lab registration.",
            "url": "https://lab.invalid/agents/time-off-coverage",
            "provider": {"id": "Provider=SELF-BUILT"},
            "platform": {"id": "Platform=OTHER"},
            "version": "0.1.0",
            "capabilities": {"streaming": False},
            "skills": [
                {
                    "id": "read-balance",
                    "name": "read-balance",
                    "description": "Read a balance.",
                    "tags": [{"tag": "read"}],
                }
            ],
            "workdayConfig": [
                {
                    "skillId": "read-balance",
                    "executionMode": {"id": "Mode=Delegate"},
                    "workdayResources": [{"tool_name": "get_time_off_balance"}],
                }
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert token.secret not in created.text


def test_cli_preflight_exits_zero() -> None:
    assert main(["preflight"]) == 0


def test_story_route_returns_the_field_report() -> None:
    client = TestClient(create_app(Runtime(load_package())))
    response = client.get("/story")
    assert response.status_code == 200
    body = response.json()
    assert body["failed"] == 0
    assert body["tokens"] == 0
    assert body["hosted_llm"] == "not-run"
    assert "lab-token-" not in response.text

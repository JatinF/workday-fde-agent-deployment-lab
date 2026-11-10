"""Troubleshooting suite. Every case is a local stand-in, not a tenant incident."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

from fde_lab.asor import AsorService, build_registration
from fde_lab.gates import all_gates
from fde_lab.load import load_package
from fde_lab.models import FailureClass, Faults, InvokeRequest, LabPackage, Outcome
from fde_lab.preflight import preflight
from fde_lab.prompts import attach_required_prompts
from fde_lab.rca import class_for, section_for
from fde_lab.runtime import Runtime

_VACATION = "fde00000000000000000000000000031"


class SuiteCaseResult(BaseModel):
    case_id: str
    expected_class: FailureClass
    actual_class: FailureClass
    expected_outcome: Outcome
    actual_outcome: Outcome
    passed: bool
    runbook_section: str
    detail: str


class SuiteReport(BaseModel):
    case_count: int
    passed: int
    failed: int
    token_leak_count: int
    business_process_events_after_replay: int
    external_calls_after_replay: int
    suite_duration_ms: float
    gates: dict[str, str]
    results: list[SuiteCaseResult] = Field(default_factory=list)


def _write(
    actor: str,
    worker: str,
    hours: int,
    request_id: str,
    faults: Faults | None = None,
) -> InvokeRequest:
    return InvokeRequest(
        actor_id=actor,
        skill="request-coverage",
        arguments={
            "worker_id": worker,
            "hours": hours,
            "time_off_type_wid": _VACATION,
            "client_request_id": request_id,
            "coverage_note": "Desk coverage for the lab engagement.",
        },
        faults=faults or Faults(),
    )


def _result(
    case_id: str,
    expected_class: FailureClass,
    actual_class: FailureClass,
    expected_outcome: Outcome,
    actual_outcome: Outcome,
    section: str,
    detail: str,
) -> SuiteCaseResult:
    return SuiteCaseResult(
        case_id=case_id,
        expected_class=expected_class,
        actual_class=actual_class,
        expected_outcome=expected_outcome,
        actual_outcome=actual_outcome,
        passed=expected_class == actual_class and expected_outcome == actual_outcome,
        runbook_section=section,
        detail=detail,
    )


def _invoke(
    case_id: str,
    runtime: Runtime,
    request: InvokeRequest,
    expected_class: FailureClass,
    expected_outcome: Outcome,
) -> tuple[SuiteCaseResult, int]:
    trace = runtime.invoke(request)
    leaks = trace.model_dump_json().count("lab-token-")
    row = _result(
        case_id,
        expected_class,
        trace.failure_class,
        expected_outcome,
        trace.outcome,
        trace.runbook_section,
        trace.code,
    )
    if case_id == "secret-redacted" and leaks:
        row.passed = False
        row.detail = "token leaked into the trace"
    return row, leaks


def run_suite(package: LabPackage | None = None) -> SuiteReport:
    loaded = package or load_package()
    started = time.perf_counter()
    rows: list[SuiteCaseResult] = []
    leaks = 0
    write_runtime = Runtime(loaded)

    def fresh() -> Runtime:
        return Runtime(loaded)

    def add(row: SuiteCaseResult, leak_count: int = 0) -> None:
        nonlocal leaks
        rows.append(row)
        leaks += leak_count

    row, leak_count = _invoke(
        "happy-read",
        fresh(),
        InvokeRequest(
            actor_id="SYN-USER-NOOR",
            skill="read-balance",
            arguments={"worker_id": "SYN-USER-IVAN"},
        ),
        FailureClass.OK,
        Outcome.COMPLETED,
    )
    add(row, leak_count)
    row, leak_count = _invoke(
        "hr-read",
        fresh(),
        InvokeRequest(
            actor_id="SYN-USER-HANA",
            skill="read-balance",
            arguments={"worker_id": "SYN-USER-OTTO"},
        ),
        FailureClass.OK,
        Outcome.COMPLETED,
    )
    add(row, leak_count)
    row, leak_count = _invoke(
        "outside-org",
        fresh(),
        InvokeRequest(
            actor_id="SYN-USER-NOOR",
            skill="read-balance",
            arguments={"worker_id": "SYN-USER-OTTO"},
        ),
        FailureClass.PERMISSION,
        Outcome.FAILED,
    )
    add(row, leak_count)
    row, leak_count = _invoke(
        "happy-write",
        write_runtime,
        _write("SYN-USER-NOOR", "SYN-USER-IVAN", 8, "req-1"),
        FailureClass.OK,
        Outcome.COMPLETED,
    )
    add(row, leak_count)
    row, leak_count = _invoke(
        "replay-write",
        write_runtime,
        _write("SYN-USER-NOOR", "SYN-USER-IVAN", 8, "req-1"),
        FailureClass.OK,
        Outcome.COMPLETED,
    )
    add(row, leak_count)
    scenarios: list[tuple[str, InvokeRequest, FailureClass, Outcome]] = [
        (
            "write-outside-org",
            _write("SYN-USER-NOOR", "SYN-USER-OTTO", 4, "req-otto"),
            FailureClass.PERMISSION,
            Outcome.FAILED,
        ),
        (
            "insufficient-balance",
            _write("SYN-USER-NOOR", "SYN-USER-IVAN", 40, "req-balance"),
            FailureClass.BUSINESS_RULE,
            Outcome.COMPLETED_WITH_ERRORS,
        ),
        (
            "tenant-not-deployed",
            _write("SYN-USER-NOOR", "SYN-USER-IVAN", 8, "req-deploy", Faults(undeployed=True)),
            FailureClass.TENANT_DEPLOYMENT,
            Outcome.NOT_LISTED,
        ),
        (
            "skill-disabled",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-skill",
                Faults(disable_skill="request-coverage"),
            ),
            FailureClass.CONFIGURATION,
            Outcome.NOT_LISTED,
        ),
        (
            "user-not-in-group",
            _write("SYN-USER-IVAN", "SYN-USER-IVAN", 8, "req-ivan"),
            FailureClass.PERMISSION,
            Outcome.NOT_LISTED,
        ),
        (
            "hr-write-hidden",
            _write("SYN-USER-HANA", "SYN-USER-OTTO", 4, "req-hana"),
            FailureClass.PERMISSION,
            Outcome.NOT_LISTED,
        ),
        (
            "unknown-tool",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-unknown",
                Faults(call_tool_name="not-a-tool"),
            ),
            FailureClass.MISSING_TOOL,
            Outcome.FAILED,
        ),
        (
            "wid-missing",
            InvokeRequest(
                actor_id="SYN-USER-NOOR",
                skill="read-balance",
                arguments={"worker_id": "SYN-USER-IVAN"},
                faults=Faults(drop_tool_wids=["wql_get"]),
            ),
            FailureClass.MISSING_RESOURCE,
            Outcome.FAILED,
        ),
        (
            "prompt-wid-missing",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-prompt",
                Faults(drop_tool_wids=["list_time_off_types"]),
            ),
            FailureClass.MISSING_RESOURCE,
            Outcome.FAILED,
        ),
        (
            "malformed-input",
            InvokeRequest(
                actor_id="SYN-USER-NOOR",
                skill="request-coverage",
                arguments={"worker_id": "SYN-USER-IVAN", "client_request_id": "req-bad"},
            ),
            FailureClass.MALFORMED_INPUT,
            Outcome.FAILED,
        ),
        (
            "rest-403",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-rest",
                Faults(call_tool_name="get_worker", rest_status=403),
            ),
            FailureClass.PERMISSION,
            Outcome.FAILED,
        ),
        (
            "soap-401",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-soap",
                Faults(call_tool_name="soap_submit_time_off", soap_status=401),
            ),
            FailureClass.PERMISSION,
            Outcome.FAILED,
        ),
        (
            "bp-not-authorized",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-bp",
                Faults(bp_unauthorized=True),
            ),
            FailureClass.PERMISSION,
            Outcome.FAILED,
        ),
        (
            "timeout",
            _write("SYN-USER-NOOR", "SYN-USER-IVAN", 8, "req-time", Faults(timeout=True)),
            FailureClass.TIMEOUT,
            Outcome.TIMED_OUT,
        ),
        (
            "retry-then-success",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-retry",
                Faults(external_failures_before_success=2),
            ),
            FailureClass.OK,
            Outcome.COMPLETED,
        ),
        (
            "retry-exhausted",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-giveup",
                Faults(external_always_fail=True),
            ),
            FailureClass.RETRY_EXHAUSTED,
            Outcome.FAILED,
        ),
        (
            "stale-token",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-stale",
                Faults(registration_epoch=2),
            ),
            FailureClass.AUTHENTICATION,
            Outcome.FAILED,
        ),
        (
            "missing-tenant-alias",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-alias",
                Faults(tenant_alias_missing=True),
            ),
            FailureClass.CONFIGURATION,
            Outcome.FAILED,
        ),
        (
            "direct-api-blocked",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-direct",
                Faults(direct_api=True),
            ),
            FailureClass.CONFIGURATION,
            Outcome.FAILED,
        ),
        (
            "response-too-large",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-size",
                Faults(declared_response_bytes=2_000_000),
            ),
            FailureClass.CONFIGURATION,
            Outcome.FAILED,
        ),
        (
            "secret-redacted",
            _write(
                "SYN-USER-NOOR",
                "SYN-USER-IVAN",
                8,
                "req-secret",
                Faults(leak_token_in_tool_body=True),
            ),
            FailureClass.OK,
            Outcome.COMPLETED,
        ),
    ]
    for case_id, request, expected_class, expected_outcome in scenarios:
        row, leak_count = _invoke(case_id, fresh(), request, expected_class, expected_outcome)
        add(row, leak_count)
    for row in _asor_rows(loaded):
        add(row)
    add(_prompt_fix(loaded))
    add(_employee_write(loaded))
    add(_ambient(loaded))
    passed = sum(1 for row in rows if row.passed)
    duration_ms = (time.perf_counter() - started) * 1000
    return SuiteReport(
        case_count=len(rows),
        passed=passed,
        failed=len(rows) - passed,
        token_leak_count=leaks,
        business_process_events_after_replay=len(write_runtime.state.events),
        external_calls_after_replay=write_runtime.state.external_calls,
        suite_duration_ms=round(duration_ms, 4),
        gates={gate.name: gate.status for gate in all_gates()},
        results=rows,
    )


def _status_row(
    case_id: str,
    status: int,
    expected_status: int,
    code: str,
    expected_class: FailureClass,
) -> SuiteCaseResult:
    matched = status == expected_status
    return _result(
        case_id,
        expected_class,
        class_for(code) if matched else FailureClass.OK,
        Outcome.FAILED,
        Outcome.FAILED if matched else Outcome.COMPLETED,
        section_for(code),
        str(status),
    )


def _asor_rows(package: LabPackage) -> list[SuiteCaseResult]:
    service = AsorService()
    runtime = Runtime(package)
    token = runtime.tokens.issue("SYN-USER-NOOR", 1, valid=True)
    state = runtime.state
    body = build_registration(package)
    rejected = service.post({}, token, {"Development"}, state)
    unauthorized = service.post(body, None, {"Development"}, state)
    forbidden = service.post(body, token, set(), state)
    missing = service.get("asor-missing", token, {"Setup: Agents"}, state)
    created = service.post(body, token, {"Development"}, state)
    updated = service.post(body, token, {"Development"}, state)
    update_ok = (
        created.status == 201
        and created.body.get("updated") is False
        and updated.status == 201
        and updated.body.get("updated") is True
        and len(state.asor_records) == 1
    )
    return [
        _status_row("asor-400", rejected.status, 400, rejected.code, FailureClass.CONFIGURATION),
        _status_row(
            "asor-401",
            unauthorized.status,
            401,
            unauthorized.code,
            FailureClass.AUTHENTICATION,
        ),
        _status_row("asor-403", forbidden.status, 403, forbidden.code, FailureClass.PERMISSION),
        _status_row(
            "asor-404",
            missing.status,
            404,
            missing.code,
            FailureClass.MISSING_RESOURCE,
        ),
        _result(
            "asor-update",
            FailureClass.OK,
            FailureClass.OK if update_ok else FailureClass.CONFIGURATION,
            Outcome.COMPLETED,
            Outcome.COMPLETED if update_ok else Outcome.FAILED,
            section_for("asor_validation"),
            "same name, provider, and version update the existing agent",
        ),
    ]


def _prompt_fix(package: LabPackage) -> SuiteCaseResult:
    skill = package.skills["request-coverage"]
    broken_tools = [name for name in skill.allowed_tools if name != "list_time_off_types"]
    broken_wids = {
        name: wid for name, wid in skill.tool_wids.items() if name != "list_time_off_types"
    }
    broken = skill.model_copy(update={"allowed_tools": broken_tools, "tool_wids": broken_wids})
    broken_package = package.model_copy(
        update={"skills": {**package.skills, "request-coverage": broken}}
    )
    before = [item.code for item in preflight(broken_package)]
    repaired = attach_required_prompts(broken, package.catalog)
    repaired_package = package.model_copy(
        update={"skills": {**package.skills, "request-coverage": repaired}}
    )
    after = [item.code for item in preflight(repaired_package) if item.severity == "error"]
    ok = "prompt_tool_missing" in before and not after
    return _result(
        "prompt-tool-fix",
        FailureClass.OK,
        FailureClass.OK if ok else FailureClass.MISSING_RESOURCE,
        Outcome.COMPLETED,
        Outcome.COMPLETED if ok else Outcome.FAILED,
        section_for("prompt_tool_missing"),
        "attach_required_prompts removes the prompt-tool finding",
    )


def _employee_write(package: LabPackage) -> SuiteCaseResult:
    security = package.security.model_copy(deep=True)
    security.skills["request-coverage"].available_to.append("SYN-SG-EMPLOYEE")
    mutated = package.model_copy(update={"security": security})
    codes = [item.code for item in preflight(mutated)]
    ok = "employee_on_write" in codes
    return _result(
        "employee-on-write",
        FailureClass.CONFIGURATION,
        FailureClass.CONFIGURATION if ok else FailureClass.OK,
        Outcome.COMPLETED,
        Outcome.COMPLETED if ok else Outcome.FAILED,
        section_for("employee_on_write"),
        "employee_on_write" if ok else "finding missing",
    )


def _ambient(package: LabPackage) -> SuiteCaseResult:
    security = package.security.model_copy(deep=True)
    security.execution_mode = "Ambient"
    mutated = package.model_copy(update={"security": security})
    codes = [item.code for item in preflight(mutated)]
    ok = "ambient_custom_agent" in codes
    return _result(
        "ambient-custom-agent",
        FailureClass.CONFIGURATION,
        FailureClass.CONFIGURATION if ok else FailureClass.OK,
        Outcome.COMPLETED,
        Outcome.COMPLETED if ok else Outcome.FAILED,
        section_for("ambient_custom_agent"),
        "ambient_custom_agent" if ok else "finding missing",
    )


def format_report(report: SuiteReport) -> str:
    lines = [
        "# Troubleshooting suite",
        "",
        "Local stand-in only. No Workday tenant was called.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Cases | " + str(report.case_count) + " |",
        "| Passed | " + str(report.passed) + " |",
        "| Failed | " + str(report.failed) + " |",
        "| Token leak count | " + str(report.token_leak_count) + " |",
        "| Business process events after replay | "
        + str(report.business_process_events_after_replay)
        + " |",
        "| External calls after replay | " + str(report.external_calls_after_replay) + " |",
        "| Suite duration ms | " + str(report.suite_duration_ms) + " |",
        "",
        "| Case | Class | Outcome | Passed | Runbook |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report.results:
        lines.append(
            "| "
            + row.case_id
            + " | "
            + row.actual_class.value
            + " | "
            + row.actual_outcome.value
            + " | "
            + str(row.passed)
            + " | "
            + row.runbook_section
            + " |"
        )
    lines.append("")
    lines.append("## Gates")
    lines.append("")
    for name, status in report.gates.items():
        lines.append("- " + name + ": " + status)
    lines.append("")
    return "\n".join(lines)

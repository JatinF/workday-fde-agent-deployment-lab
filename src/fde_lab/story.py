"""One field story: a time-off request, ten injected failures, and one productized fix.

The people and the coverage calendar are fixtures. No model is called. No Workday
tenant is called. Tokens are 0.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from fde_lab.asor import AsorService, build_registration
from fde_lab.load import load_package
from fde_lab.models import Faults, InvokeRequest, LabPackage, LabState, Trace
from fde_lab.paths import repo_root
from fde_lab.preflight import preflight
from fde_lab.prompts import attach_required_prompts
from fde_lab.runtime import Runtime
from fde_lab.tokens import TokenBook

_VACATION = "fde00000000000000000000000000031"
_ORDER = (
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
)
_HAPPY_TAIL = [
    "validate_input",
    "read_worker",
    "read_balance",
    "reserve_coverage",
    "submit_business_process",
]
_BACKLOG_ID = "FDE-BACKLOG-001"


class ScenarioFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    symptom: str
    diagnosis: str
    root_cause: str
    fix: str
    prevention: str
    actor_id: str
    skill: str
    arguments: dict[str, str | int]
    faults: Faults = Field(default_factory=Faults)
    expected_code: str
    validation: Literal[
        "clean_write",
        "replay",
        "retry_recover",
        "least_privilege",
        "asor_token",
    ]


class HappyPath(BaseModel):
    code: str
    trace_id: str
    event_id: str
    external_calls: int
    retry_attempts: int
    nodes: list[str]
    passed: bool


class Incident(BaseModel):
    scenario_id: str
    title: str
    symptom: str
    telemetry: str
    diagnosis: str
    root_cause: str
    fix: str
    validation: str
    prevention: str
    expected_code: str
    actual_code: str
    passed: bool


class Lifecycle(BaseModel):
    backlog_id: str
    field_issue: str
    before_codes: list[str]
    after_error_count: int
    repaired_invoke_code: str
    passed: bool


class StoryReport(BaseModel):
    tokens: int = 0
    hosted_llm: str = "not-run"
    happy_path: HappyPath
    incidents: list[Incident]
    lifecycle: Lifecycle
    contract_findings: list[str]
    passed: int
    failed: int
    duration_ms: float


def run_story(root: Path | None = None) -> StoryReport:
    started = time.perf_counter()
    base = root or repo_root()
    package = load_package(base)
    happy = _happy(package)
    incidents = [_incident(package, scenario) for scenario in _scenarios(base)]
    lifecycle = _lifecycle(package)
    findings = _policy_findings(base) + _template_findings(base, package)
    failed_parts = [
        0 if happy.passed else 1,
        sum(0 if item.passed else 1 for item in incidents),
        0 if lifecycle.passed else 1,
        1 if findings else 0,
    ]
    failed = sum(failed_parts)
    total = 2 + len(incidents) + 1
    duration_ms = round((time.perf_counter() - started) * 1000, 4)
    return StoryReport(
        happy_path=happy,
        incidents=incidents,
        lifecycle=lifecycle,
        contract_findings=findings,
        passed=total - failed,
        failed=failed,
        duration_ms=duration_ms,
    )


def format_story(report: StoryReport) -> str:
    happy = report.happy_path
    lines = [
        "# Field story",
        "",
        "Synthetic engagement SYN-ORG-NORTHLINE. No model is called. No Workday tenant was called.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Tokens | " + str(report.tokens) + " |",
        "| Hosted model | " + report.hosted_llm + " |",
        "| Happy-path code | " + happy.code + " |",
        "| Trace | " + happy.trace_id + " |",
        "| Business-process event | " + happy.event_id + " |",
        "| External coverage calls | " + str(happy.external_calls) + " |",
        "| Retry attempts | " + str(happy.retry_attempts) + " |",
        "| Nodes | " + " > ".join(happy.nodes) + " |",
        "| Checks passed | " + str(report.passed) + " |",
        "| Checks failed | " + str(report.failed) + " |",
        "| Duration ms | " + str(report.duration_ms) + " |",
        "",
        "## Flow",
        "",
        "SYN-USER-NOOR submits 8 hours for SYN-USER-IVAN. CoverageInput accepts the payload.",
        "No model is called. The gateway then checks the token, the deploy, Available To,",
        "the tool, and the domain. The action reads the worker and the balance, reserves one",
        "coverage slot, and submits one Request Time Off event. The event row is the audit",
        "record. The trace is the telemetry. A failed dependency does not submit the process.",
        "",
        "## Lifecycle " + report.lifecycle.backlog_id,
        "",
        report.lifecycle.field_issue,
        "",
        "Before: " + ", ".join(report.lifecycle.before_codes) + ".",
        "After error count: " + str(report.lifecycle.after_error_count) + ".",
        "Repaired invoke: " + report.lifecycle.repaired_invoke_code + ".",
        "",
        "## Incidents",
        "",
    ]
    for item in report.incidents:
        lines.extend(
            [
                "### " + item.scenario_id,
                "",
                item.title,
                "",
                "- Symptom: " + item.symptom,
                "- Telemetry: " + item.telemetry,
                "- Diagnosis: " + item.diagnosis,
                "- Root cause: " + item.root_cause,
                "- Fix: " + item.fix,
                "- Validation: " + item.validation,
                "- Prevention: " + item.prevention,
                "",
            ]
        )
    lines.append("## Contract findings")
    lines.append("")
    if report.contract_findings:
        lines.extend("- " + item for item in report.contract_findings)
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def _clean_request(request_id: str) -> InvokeRequest:
    return InvokeRequest(
        actor_id="SYN-USER-NOOR",
        skill="request-coverage",
        arguments={
            "worker_id": "SYN-USER-IVAN",
            "hours": 8,
            "time_off_type_wid": _VACATION,
            "client_request_id": request_id,
            "coverage_note": "Desk coverage for the lab engagement.",
        },
    )


def _happy(package: LabPackage) -> HappyPath:
    runtime = Runtime(package)
    trace = runtime.invoke(_clean_request("story-happy"))
    names = [node.name for node in trace.nodes]
    tail_ok = "validate_input" in names and names[names.index("validate_input") :] == _HAPPY_TAIL
    event_id = trace.business_process_event_id or ""
    passed = (
        trace.code == "ok"
        and names[:1] == ["token_check"]
        and "gateway_authorize" in names
        and tail_ok
        and event_id != ""
        and runtime.state.external_calls == 1
        and len(runtime.state.events) == 1
        and trace.retry_attempts == 1
    )
    return HappyPath(
        code=trace.code,
        trace_id=trace.trace_id,
        event_id=event_id,
        external_calls=runtime.state.external_calls,
        retry_attempts=trace.retry_attempts,
        nodes=names,
        passed=passed,
    )


def _scenarios(root: Path) -> list[ScenarioFile]:
    base = root / "failure_scenarios"
    found = [path.parent.name for path in base.glob("*/scenario.yaml")]
    if set(found) != set(_ORDER) or len(found) != len(_ORDER):
        raise ValueError("failure scenario folders do not match the field story")
    loaded: list[ScenarioFile] = []
    for name in _ORDER:
        scenario = ScenarioFile.model_validate(_yaml_dict(base / name / "scenario.yaml"))
        if scenario.id != name:
            raise ValueError("scenario id " + scenario.id)
        loaded.append(scenario)
    return loaded


def _incident(package: LabPackage, scenario: ScenarioFile) -> Incident:
    runtime = Runtime(package)
    request = InvokeRequest(
        actor_id=scenario.actor_id,
        skill=scenario.skill,
        arguments=scenario.arguments,
        faults=scenario.faults,
    )
    if scenario.validation == "replay":
        first = runtime.invoke(request.model_copy(update={"faults": Faults()}))
        second = runtime.invoke(request.model_copy(update={"faults": Faults()}))
        actual = second.code
        validation = (
            "first="
            + first.code
            + " second="
            + second.code
            + " events="
            + str(len(runtime.state.events))
            + " external_calls="
            + str(runtime.state.external_calls)
        )
        passed = (
            first.code == "ok"
            and second.code == scenario.expected_code
            and len(runtime.state.events) == 1
            and runtime.state.external_calls == 1
        )
        return _incident_row(scenario, _telemetry(second), validation, actual, passed)
    trace = runtime.invoke(request)
    telemetry = _telemetry(trace)
    passed, validation = _validate(package, scenario, trace)
    if scenario.validation == "asor_token":
        rejected, accepted = _registration_probe(package)
        telemetry = telemetry + " asor_http=" + str(rejected)
        validation = (
            "asor_rejected="
            + str(rejected)
            + " asor_registered="
            + str(accepted)
            + " "
            + validation
        )
        passed = passed and rejected == 401 and accepted == 201
    return _incident_row(scenario, telemetry, validation, trace.code, passed)


def _incident_row(
    scenario: ScenarioFile,
    telemetry: str,
    validation: str,
    actual: str,
    passed: bool,
) -> Incident:
    return Incident(
        scenario_id=scenario.id,
        title=scenario.title,
        symptom=scenario.symptom,
        telemetry=telemetry,
        diagnosis=scenario.diagnosis,
        root_cause=scenario.root_cause,
        fix=scenario.fix,
        validation=validation,
        prevention=scenario.prevention,
        expected_code=scenario.expected_code,
        actual_code=actual,
        passed=passed and actual == scenario.expected_code,
    )


def _validate(
    package: LabPackage,
    scenario: ScenarioFile,
    trace: Trace,
) -> tuple[bool, str]:
    if scenario.validation == "least_privilege":
        read = Runtime(package).invoke(
            InvokeRequest(
                actor_id="SYN-USER-HANA",
                skill="read-balance",
                arguments={"worker_id": "SYN-USER-IVAN"},
            )
        )
        write = Runtime(package).invoke(
            InvokeRequest(
                actor_id="SYN-USER-HANA",
                skill="request-coverage",
                arguments=dict(scenario.arguments),
            )
        )
        text = "read=" + read.code + " write=" + write.code
        return read.code == "ok" and write.code == "not_in_available_to", text
    if scenario.validation == "retry_recover":
        arguments = dict(scenario.arguments)
        arguments["client_request_id"] = "story-recover-" + scenario.id
        recovered = Runtime(package).invoke(
            InvokeRequest(
                actor_id=scenario.actor_id,
                skill=scenario.skill,
                arguments=arguments,
                faults=Faults(external_failures_before_success=2),
            )
        )
        event_id = recovered.business_process_event_id or ""
        text = (
            "code="
            + recovered.code
            + " retry_attempts="
            + str(recovered.retry_attempts)
            + " event_id="
            + event_id
        )
        ok = (
            recovered.code == "ok"
            and recovered.retry_attempts == 3
            and recovered.business_process_event_id is not None
        )
        return ok, text
    if scenario.validation in {"clean_write", "asor_token"}:
        clean = Runtime(package).invoke(_clean_request("story-validate-" + scenario.id))
        event_id = clean.business_process_event_id or ""
        return clean.code == "ok" and event_id != "", "code=" + clean.code + " event_id=" + event_id
    if trace.code == scenario.expected_code:
        return True, "code=" + trace.code
    return False, "code=" + trace.code


def _registration_probe(package: LabPackage) -> tuple[int, int]:
    service = AsorService()
    state = LabState()
    body = build_registration(package)
    rejected = service.post(body, None, {"Development"}, state)
    token = TokenBook().issue("SYN-USER-NOOR", state.registration_epoch, valid=True)
    accepted = service.post(body, token, {"Development"}, state)
    return rejected.status, accepted.status


def _telemetry(trace: Trace) -> str:
    names = ",".join(node.name for node in trace.nodes)
    return (
        "code="
        + trace.code
        + " class="
        + trace.failure_class.value
        + " outcome="
        + trace.outcome.value
        + " nodes="
        + names
    )


def _lifecycle(package: LabPackage) -> Lifecycle:
    skill = package.skills["request-coverage"]
    broken_tools = [name for name in skill.allowed_tools if name != "list_time_off_types"]
    broken_wids = {
        name: wid for name, wid in skill.tool_wids.items() if name != "list_time_off_types"
    }
    broken = skill.model_copy(update={"allowed_tools": broken_tools, "tool_wids": broken_wids})
    broken_package = package.model_copy(
        update={"skills": {**package.skills, "request-coverage": broken}}
    )
    before = [item.code for item in preflight(broken_package) if item.severity == "error"]
    repaired = attach_required_prompts(broken, package.catalog)
    repaired_package = package.model_copy(
        update={"skills": {**package.skills, "request-coverage": repaired}}
    )
    after = [item for item in preflight(repaired_package) if item.severity == "error"]
    trace = Runtime(repaired_package).invoke(_clean_request("story-lifecycle"))
    shipped = [item for item in preflight(package) if item.severity == "error"]
    passed = (
        "prompt_tool_missing" in before
        and after == []
        and shipped == []
        and trace.code == "ok"
        and trace.business_process_event_id is not None
    )
    return Lifecycle(
        backlog_id=_BACKLOG_ID,
        field_issue=(
            "The write skill was loaded without list_time_off_types. "
            "Preflight reports prompt_tool_missing. attach_required_prompts restores the "
            "catalog WID, and the repaired package submits one Request Time Off event. "
            "This was reproduced in the lab from the prompt-tool rule. It was not observed "
            "in a customer tenant."
        ),
        before_codes=before,
        after_error_count=len(after),
        repaired_invoke_code=trace.code,
        passed=passed,
    )


def _policy_findings(root: Path) -> list[str]:
    path = root / "security" / "policies.py"
    spec = importlib.util.spec_from_file_location("fde_security_policies", path)
    if spec is None or spec.loader is None:
        return ["security policies module missing"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = getattr(module, "template_findings", None)
    if not callable(raw):
        return ["template_findings missing"]
    result = raw(root)
    if not isinstance(result, list):
        return ["template_findings type"]
    findings: list[str] = []
    for item in result:
        if not isinstance(item, str):
            return ["template_findings type"]
        findings.append(item)
    return findings


def _template_findings(root: Path, package: LabPackage) -> list[str]:
    findings: list[str] = []
    findings.extend(_agent_findings(root, package))
    findings.extend(_workflow_findings(root, package))
    findings.extend(_service_findings(root, package))
    return findings


def _agent_findings(root: Path, package: LabPackage) -> list[str]:
    findings: list[str] = []
    definition = _yaml_dict(root / "agent" / "agent_definition" / "index.yaml")
    agent_file = definition.get("agent_file")
    if not isinstance(agent_file, str) or not (root / agent_file).is_file():
        findings.append("agent_definition.agent_file")
    if definition.get("name") != package.agent.name:
        findings.append("agent_definition.name")
    if definition.get("mode") != package.security.execution_mode:
        findings.append("agent_definition.mode")
    skills = _yaml_dict(root / "agent" / "skills" / "index.yaml").get("skills")
    if not isinstance(skills, list):
        findings.append("skills.index")
    else:
        names: list[str] = []
        for row in skills:
            if not isinstance(row, dict):
                findings.append("skills.row")
                continue
            file_name = row.get("file")
            skill_name = row.get("name")
            if not isinstance(file_name, str) or not (root / file_name).is_file():
                findings.append("skills.file")
            if isinstance(skill_name, str):
                names.append(skill_name)
        if names != list(package.agent.skills):
            findings.append("skills.names")
    prompts = _yaml_dict(root / "agent" / "prompts" / "time-off-types.yaml").get("prompt_values")
    expected = sorted((item.wid, item.label) for item in package.catalog.prompt_values.values())
    actual: list[tuple[str, str]] = []
    if isinstance(prompts, list):
        for row in prompts:
            if isinstance(row, dict) and isinstance(row.get("wid"), str):
                label = row.get("label")
                wid = row.get("wid")
                if isinstance(wid, str) and isinstance(label, str):
                    actual.append((wid, label))
    if sorted(actual) != expected:
        findings.append("prompts.time_off_types")
    policy = _yaml_dict(root / "agent" / "policies" / "delegate.yaml")
    if policy.get("execution_mode") != package.security.execution_mode:
        findings.append("policies.execution_mode")
    if policy.get("app_id") != package.security.app_id:
        findings.append("policies.app_id")
    if policy.get("version") != package.security.version:
        findings.append("policies.version")
    return findings


def _workflow_findings(root: Path, package: LabPackage) -> list[str]:
    findings: list[str] = []
    operation = _yaml_dict(root / "workflows" / "employee_operations" / "request-time-off.yaml")
    if operation.get("process") != "Request Time Off":
        findings.append("workflow.process")
    if operation.get("steps") != package.orchestration.steps:
        findings.append("workflow.steps")
    approval = _yaml_dict(root / "workflows" / "approvals" / "manager-chain.yaml")
    if approval.get("submit_requires") != "manager_of_worker":
        findings.append("workflow.submit_requires")
    if approval.get("hr_may_read") is not True or approval.get("hr_may_submit") is not False:
        findings.append("workflow.hr")
    external = _yaml_dict(root / "workflows" / "external_actions" / "coverage-calendar.yaml")
    service = _yaml_dict(root / "services" / "integrations" / "coverage-calendar.yaml")
    if external != service:
        findings.append("coverage.template_drift")
    if external.get("url") != "https://coverage.lab.invalid/slots":
        findings.append("coverage.url")
    if external.get("live_call") != "not-run":
        findings.append("coverage.live_call")
    if external.get("max_attempts") != package.orchestration.retry.max_attempts:
        findings.append("coverage.max_attempts")
    if external.get("timeout_ms") != package.orchestration.timeout_ms:
        findings.append("coverage.timeout_ms")
    registration = build_registration(package)
    if "https://coverage.lab.invalid/slots" not in str(registration):
        findings.append("coverage.registration")
    return findings


def _service_findings(root: Path, package: LabPackage) -> list[str]:
    findings: list[str] = []
    boundary = _yaml_dict(root / "services" / "workday" / "boundary.yaml")
    if boundary.get("live_calls") != "not-run" or boundary.get("called") is not False:
        findings.append("workday.boundary")
    fields = _yaml_dict(root / "services" / "telemetry" / "trace-fields.yaml").get("fields")
    trace_fields = set(Trace.model_fields)
    if not isinstance(fields, list) or any(not isinstance(item, str) for item in fields):
        findings.append("telemetry.fields")
    elif any(item not in trace_fields for item in fields if isinstance(item, str)):
        findings.append("telemetry.unknown_field")
    routes = _yaml_dict(root / "services" / "api" / "routes.yaml").get("paths")
    if not isinstance(routes, list):
        findings.append("api.routes")
    else:
        from fde_lab.api import create_app

        live = set(create_app().openapi()["paths"])
        declared = {item for item in routes if isinstance(item, str)}
        if declared != live:
            findings.append("api.routes")
    if package.security.version != "0.1.0":
        findings.append("package.version")
    return findings


def _yaml_dict(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected a mapping at " + str(path))
    parsed: dict[str, object] = {}
    for key, value in loaded.items():
        parsed[str(key)] = value
    return parsed

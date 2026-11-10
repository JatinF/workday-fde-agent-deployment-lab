"""Run the Custom Agent Action stand-in.

The Idempotent effect is a Workday annotation. The replay store is the lab control
that makes a repeated client_request_id return the original business-process event.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, ValidationError

from fde_lab.models import (
    BusinessProcessEvent,
    Catalog,
    Faults,
    LabState,
    Orchestration,
    TenantData,
    TraceNode,
)
from fde_lab.tokens import redact_obj


class Clock:
    def __init__(self) -> None:
        self.now_ms = 0

    def advance(self, amount: int) -> None:
        self.now_ms += amount


class CoverageInput(BaseModel):
    """Strict so a string hour stays a schema mismatch instead of a coerced int."""

    model_config = ConfigDict(extra="forbid", strict=True)

    worker_id: str
    hours: int
    time_off_type_wid: str
    client_request_id: str
    coverage_note: str = ""


class StepResult(BaseModel):
    code: str
    message: str
    event_id: str | None = None
    retry_attempts: int = 0
    nodes: list[TraceNode]


def _node(
    name: str,
    status: str,
    inputs: Mapping[str, object],
    outputs: Mapping[str, object],
) -> TraceNode:
    redacted_in = redact_obj(inputs)
    redacted_out = redact_obj(outputs)
    assert isinstance(redacted_in, dict)
    assert isinstance(redacted_out, dict)
    return TraceNode(name=name, status=status, inputs=redacted_in, outputs=redacted_out)


def _validation_code(exc: ValidationError) -> str:
    for err in exc.errors():
        kind = str(err["type"])
        if kind.endswith("_type") or kind.endswith("_parsing"):
            return "schema_mismatch"
    return "malformed_input"


def _idempotency_key(actor_id: str, payload: CoverageInput) -> str:
    return actor_id + "|" + payload.worker_id + "|" + payload.client_request_id


def run_coverage(
    *,
    orchestration: Orchestration,
    catalog: Catalog,
    tenant: TenantData,
    state: LabState,
    actor_id: str,
    actor_groups: list[str],
    arguments: dict[str, str | int],
    faults: Faults,
    token_secret: str,
    clock: Clock,
) -> StepResult:
    try:
        payload = CoverageInput.model_validate(arguments)
    except ValidationError as exc:
        code = _validation_code(exc)
        return StepResult(
            code=code,
            message=str(exc.error_count()) + " input field(s) rejected",
            nodes=[
                _node(
                    "validate_input",
                    "failed",
                    arguments,
                    {"error_count": exc.error_count(), "code": code},
                )
            ],
        )
    key = _idempotency_key(actor_id, payload)
    existing = state.idempotency.get(key)
    if existing:
        return StepResult(
            code="replayed",
            message="Returned the stored Request Time Off event.",
            event_id=existing,
            nodes=[
                _node(
                    "idempotency",
                    "replayed",
                    {"client_request_id": payload.client_request_id},
                    {"event_id": existing},
                )
            ],
        )
    if payload.time_off_type_wid not in catalog.prompt_values:
        return StepResult(
            code="malformed_input",
            message="time_off_type_wid is not a prompt value.",
            nodes=[
                _node(
                    "validate_input",
                    "failed",
                    {"time_off_type_wid": payload.time_off_type_wid},
                    {},
                )
            ],
        )
    worker = tenant.worker(payload.worker_id)
    if worker is None:
        return StepResult(
            code="malformed_input",
            message="worker_id is not in the lab tenant.",
            nodes=[_node("read_worker", "failed", {"worker_id": payload.worker_id}, {})],
        )
    is_hr = "SYN-SG-HR-PARTNER" in actor_groups
    in_chain = worker.manager_id == actor_id
    if not in_chain and not is_hr:
        return StepResult(
            code="outside_management_chain",
            message="The actor is outside this worker's management chain.",
            nodes=[_node("read_worker", "denied", {"worker_id": payload.worker_id}, {})],
        )
    if not in_chain:
        return StepResult(
            code="outside_management_chain",
            message="Only the worker's manager can submit Request Time Off.",
            nodes=[_node("read_worker", "denied", {"worker_id": payload.worker_id}, {})],
        )
    if payload.hours <= 0 or payload.hours > worker.balance_hours:
        return StepResult(
            code="insufficient_balance",
            message="Requested hours are outside the remaining balance.",
            nodes=[
                _node(
                    "read_balance",
                    "rejected",
                    {"hours": payload.hours},
                    {"balance_hours": worker.balance_hours},
                )
            ],
        )
    read_nodes = [
        _node(
            "validate_input",
            "completed",
            {"client_request_id": payload.client_request_id},
            {"hours": payload.hours},
        ),
        _node(
            "read_worker",
            "completed",
            {"worker_id": payload.worker_id},
            {"manager_id": worker.manager_id or ""},
        ),
        _node(
            "read_balance",
            "completed",
            {"hours": payload.hours},
            {"balance_hours": worker.balance_hours},
        ),
    ]
    if faults.bp_unauthorized:
        return StepResult(
            code="task_not_authorized",
            message="The task submitted is not authorized.",
            nodes=read_nodes
            + [_node("submit_business_process", "failed", {"process": "Request Time Off"}, {})],
        )
    coverage = _reserve_coverage(orchestration, faults, token_secret, clock, state)
    if coverage.code != "ok":
        return coverage.model_copy(update={"nodes": read_nodes + coverage.nodes})
    if faults.declared_response_bytes is not None:
        if faults.declared_response_bytes > orchestration.response_limit_bytes:
            return StepResult(
                code="response_too_large",
                message="Response size too large.",
                nodes=read_nodes
                + coverage.nodes
                + [
                    _node(
                        "configure_response",
                        "failed",
                        {"declared_response_bytes": faults.declared_response_bytes},
                        {"limit": orchestration.response_limit_bytes},
                    )
                ],
            )
    event = BusinessProcessEvent(
        event_id="evt-" + str(len(state.events) + 1).zfill(4),
        process="Request Time Off",
        worker_id=payload.worker_id,
        hours=payload.hours,
        type_wid=payload.time_off_type_wid,
        client_request_id=payload.client_request_id,
        actor_id=actor_id,
    )
    state.events.append(event)
    state.idempotency[key] = event.event_id
    nodes = read_nodes + coverage.nodes + [
        _node(
            "submit_business_process",
            "completed",
            {"process": event.process, "client_request_id": payload.client_request_id},
            {"event_id": event.event_id},
        )
    ]
    return StepResult(
        code="ok",
        message="Submitted Request Time Off.",
        event_id=event.event_id,
        retry_attempts=coverage.retry_attempts,
        nodes=nodes,
    )


def _reserve_coverage(
    orchestration: Orchestration,
    faults: Faults,
    token_secret: str,
    clock: Clock,
    state: LabState,
) -> StepResult:
    attempts = 0
    nodes: list[TraceNode] = []
    while attempts < orchestration.retry.max_attempts:
        attempts += 1
        state.external_calls += 1
        if faults.timeout and attempts == 1:
            clock.advance(orchestration.timeout_ms + 1)
        elapsed = clock.now_ms
        if elapsed > orchestration.timeout_ms:
            return StepResult(
                code="timed_out",
                message="The orchestration ran longer than the synchronous limit.",
                retry_attempts=attempts,
                nodes=nodes
                + [
                    _node(
                        "reserve_coverage",
                        "timed_out",
                        {"attempt": attempts},
                        {"elapsed_ms": elapsed},
                    )
                ],
            )
        failed = faults.external_always_fail or attempts <= faults.external_failures_before_success
        raw_body = "reserved"
        if faults.leak_token_in_tool_body:
            raw_body = "upstream said Bearer " + token_secret
        if not failed:
            return StepResult(
                code="ok",
                message="Coverage slot reserved.",
                retry_attempts=attempts,
                nodes=nodes
                + [
                    _node(
                        "reserve_coverage",
                        "completed",
                        {"attempt": attempts},
                        {"body": raw_body},
                    )
                ],
            )
        nodes.append(
            _node(
                "reserve_coverage",
                "retry",
                {"attempt": attempts},
                {"status": 503, "body": raw_body},
            )
        )
        if attempts >= orchestration.retry.max_attempts:
            break
        clock.advance(_backoff(orchestration, attempts))
    return StepResult(
        code="retry_exhausted",
        message="The coverage calendar still returned an error after the retry policy.",
        retry_attempts=attempts,
        nodes=nodes,
    )


def _backoff(orchestration: Orchestration, attempt: int) -> int:
    schedule = orchestration.retry.backoff_ms
    if not schedule:
        return 0
    index = min(attempt - 1, len(schedule) - 1)
    return schedule[index]


def read_balance(
    *,
    tenant: TenantData,
    actor_id: str,
    actor_groups: list[str],
    arguments: dict[str, str | int],
) -> StepResult:
    worker_id = arguments.get("worker_id")
    if not isinstance(worker_id, str) or not worker_id:
        return StepResult(code="malformed_input", message="worker_id is required.", nodes=[])
    if list(arguments) != ["worker_id"]:
        return StepResult(
            code="malformed_input",
            message="read-balance accepts only worker_id.",
            nodes=[],
        )
    worker = tenant.worker(worker_id)
    if worker is None:
        return StepResult(
            code="malformed_input",
            message="worker_id is not in the lab tenant.",
            nodes=[],
        )
    is_hr = "SYN-SG-HR-PARTNER" in actor_groups
    in_chain = worker.manager_id == actor_id or worker.worker_id == actor_id
    if not is_hr and not in_chain:
        return StepResult(
            code="outside_management_chain",
            message="The actor is outside this worker's management chain.",
            nodes=[_node("read_balance", "denied", {"worker_id": worker_id}, {})],
        )
    return StepResult(
        code="ok",
        message="Balance read.",
        nodes=[
            _node(
                "read_balance",
                "completed",
                {"worker_id": worker_id},
                {"balance_hours": worker.balance_hours},
            )
        ],
    )

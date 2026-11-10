"""Typed contracts for the lab. These are lab models, not a Workday SDK."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FailureClass(StrEnum):
    OK = "ok"
    TENANT_DEPLOYMENT = "tenant_deployment"
    CONFIGURATION = "configuration_error"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission_failure"
    MISSING_TOOL = "missing_tool"
    MISSING_RESOURCE = "missing_resource"
    MALFORMED_INPUT = "malformed_input"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    BUSINESS_RULE = "business_rule"


class Outcome(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    NOT_LISTED = "not_listed"
    TIMED_OUT = "timed_out"


class Finding(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message: str
    section: str


class ToolDef(BaseModel):
    name: str
    wid: str
    protocol: Literal["mcp", "rest", "soap", "wql", "orchestration", "prompt"]
    operation: Literal["VIEW", "CREATE", "PATCH"]
    effect: Literal["read-only", "destructive", "idempotent"]
    domain: str
    description: str
    required_prompts: list[str] = Field(default_factory=list)
    action_id: str | None = None


class PolicyDef(BaseModel):
    groups: list[str]


class PromptValue(BaseModel):
    wid: str
    label: str


class Catalog(BaseModel):
    tools: dict[str, ToolDef]
    policies: dict[str, PolicyDef]
    prompt_values: dict[str, PromptValue]

    def tool(self, name: str) -> ToolDef | None:
        return self.tools.get(name)


class Worker(BaseModel):
    worker_id: str
    manager_id: str | None
    groups: list[str]
    balance_hours: int


class TenantData(BaseModel):
    org_id: str
    workers: dict[str, Worker]

    def worker(self, worker_id: str) -> Worker | None:
        return self.workers.get(worker_id)


class SkillArtifact(BaseModel):
    name: str
    description: str
    tags: list[str]
    allowed_tools: list[str]
    tool_wids: dict[str, str]
    body: str
    allowed_tools_form: Literal["list", "string"]
    frontmatter_opened: bool


class AgentArtifact(BaseModel):
    name: str
    description: str
    skills: list[str]
    body: str
    frontmatter_opened: bool


class SkillSecurity(BaseModel):
    enabled: bool
    available_to: list[str]


class PackageSecurity(BaseModel):
    execution_mode: str
    app_id: str
    version: str
    deployed_versions: list[str]
    skills: dict[str, SkillSecurity]
    asu_name: str
    asu_groups: list[str]


class RequestProperty(BaseModel):
    name: str
    type: Literal["string", "number"]
    required: bool
    description: str


class RetryPolicy(BaseModel):
    max_attempts: int
    backoff_ms: list[int]


class Orchestration(BaseModel):
    name: str
    template: str
    action_id: str
    display_name: str
    description: str
    effect: Literal["Destructive", "Idempotent", "Read-Only", "Open World"]
    timeout_ms: int
    response_limit_bytes: int
    retry: RetryPolicy
    request_properties: list[RequestProperty]
    headers: list[str]
    query_parameters: list[str]
    workday_tools: list[str]
    steps: list[str]


class LabPackage(BaseModel):
    agent: AgentArtifact
    skills: dict[str, SkillArtifact]
    security: PackageSecurity
    orchestration: Orchestration
    catalog: Catalog
    tenant: TenantData


class Faults(BaseModel):
    undeployed: bool = False
    disable_skill: str | None = None
    drop_tool_wids: list[str] = Field(default_factory=list)
    rest_status: int | None = None
    soap_status: int | None = None
    external_failures_before_success: int = 0
    external_always_fail: bool = False
    timeout: bool = False
    declared_response_bytes: int | None = None
    bp_unauthorized: bool = False
    token_invalid: bool = False
    registration_epoch: int | None = None
    leak_token_in_tool_body: bool = False
    tenant_alias_missing: bool = False
    call_tool_name: str | None = None
    direct_api: bool = False


class InvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str
    skill: str
    arguments: dict[str, str | int] = Field(default_factory=dict)
    faults: Faults = Field(default_factory=Faults)


class TraceNode(BaseModel):
    name: str
    status: str
    inputs: dict[str, object]
    outputs: dict[str, object]


class Trace(BaseModel):
    trace_id: str
    agent: str
    skill: str
    actor_id: str
    failure_class: FailureClass
    outcome: Outcome
    code: str
    runbook_section: str
    message: str
    nodes: list[TraceNode]
    business_process_event_id: str | None = None
    retry_attempts: int = 0


class AccessToken(BaseModel):
    subject: str
    issued_epoch: int
    valid: bool
    secret: str


class BusinessProcessEvent(BaseModel):
    event_id: str
    process: str
    worker_id: str
    hours: int
    type_wid: str
    client_request_id: str
    actor_id: str


class LabState(BaseModel):
    registration_epoch: int = 1
    events: list[BusinessProcessEvent] = Field(default_factory=list)
    idempotency: dict[str, str] = Field(default_factory=dict)
    external_calls: int = 0
    asor_records: dict[str, dict[str, object]] = Field(default_factory=dict)


class Gate(BaseModel):
    name: str
    status: Literal["not-run", "blocked", "passed"]
    reason: str

"""Execute one skill invocation through the two documented runtime clients."""

from __future__ import annotations

from fde_lab.gateway import authorize_tool
from fde_lab.load import load_package
from fde_lab.models import InvokeRequest, LabPackage, LabState, Trace, TraceNode
from fde_lab.orchestrate import Clock, read_balance, run_coverage
from fde_lab.rca import class_for, outcome_for, section_for
from fde_lab.tokens import TokenBook, redact_obj

_MESSAGES: dict[str, str] = {
    "not_deployed": "The app version is not deployed. The tool is not listed.",
    "skill_disabled": "The skill is disabled or unknown. The tool is not listed.",
    "not_in_available_to": "The actor is outside Available To. The tool is not listed.",
    "unknown_tool": "Unknown tool.",
    "wid_missing": "The Workday resource is not registered on the skill.",
    "prompt_tool_missing": "A required prompt tool WID is missing from the skill.",
    "domain_denied": "The actor's security groups are not on the tool domain policy.",
    "rest_403": "REST call returned 403.",
    "soap_401": "SOAP call returned 401.",
    "token_invalid": "The access token was rejected.",
    "token_stale": "The token was issued before the agent registration changed.",
    "tenant_alias_missing": "Agent Gateway requires the tenant alias.",
    "direct_api_blocked": "The runtime cannot call Workday except through its tool clients.",
    "malformed_input": "The actor is not in the lab tenant.",
}


class Runtime:
    def __init__(
        self,
        package: LabPackage,
        state: LabState | None = None,
        tokens: TokenBook | None = None,
    ) -> None:
        self.package = package
        self.state = state or LabState()
        self.tokens = tokens or TokenBook()
        self.traces: dict[str, Trace] = {}
        self._sequence = 0

    @classmethod
    def load(cls, root: object = None) -> Runtime:
        from pathlib import Path

        package_root = root if isinstance(root, Path) else None
        return cls(load_package(package_root))

    def invoke(self, request: InvokeRequest) -> Trace:
        actor = self.package.tenant.worker(request.actor_id)
        epoch = (
            request.faults.registration_epoch
            if request.faults.registration_epoch is not None
            else self.state.registration_epoch
        )
        token = self.tokens.issue(
            request.actor_id,
            self.state.registration_epoch,
            valid=not request.faults.token_invalid and actor is not None,
        )
        alias = "" if request.faults.tenant_alias_missing else self.package.tenant.org_id
        nodes: list[TraceNode] = [
            TraceNode(
                name="token_check",
                status="rejected" if not token.valid else "completed",
                inputs={"actor_id": request.actor_id, "issued_epoch": token.issued_epoch},
                outputs={"registration_epoch": epoch},
            )
        ]
        if actor is None:
            return self._store(request, "malformed_input", nodes, None, 0)
        primary, dependencies = self._tools(request)
        client = "custom_agent_action" if request.skill == "request-coverage" else "mcp_client"
        for tool_name in [primary, *dependencies]:
            code = authorize_tool(
                self.package,
                actor_groups=actor.groups,
                skill_name=request.skill,
                tool_name=tool_name,
                token=token,
                faults=request.faults,
                tenant_alias=alias,
                registration_epoch=epoch,
            )
            nodes.append(
                TraceNode(
                    name="gateway_authorize",
                    status="listed" if code == "ok" else "blocked",
                    inputs={"tool_name": tool_name, "client": client},
                    outputs={"code": code},
                )
            )
            if code != "ok":
                return self._store(request, code, nodes, None, 0)
        clock = Clock()
        if request.skill == "read-balance":
            result = read_balance(
                tenant=self.package.tenant,
                actor_id=request.actor_id,
                actor_groups=actor.groups,
                arguments=request.arguments,
            )
        else:
            result = run_coverage(
                orchestration=self.package.orchestration,
                catalog=self.package.catalog,
                tenant=self.package.tenant,
                state=self.state,
                actor_id=request.actor_id,
                actor_groups=actor.groups,
                arguments=request.arguments,
                faults=request.faults,
                token_secret=token.secret,
                clock=clock,
            )
        nodes.extend(result.nodes)
        return self._store(
            request,
            result.code,
            nodes,
            result.event_id,
            result.retry_attempts,
            result.message,
        )

    def _tools(self, request: InvokeRequest) -> tuple[str, list[str]]:
        if request.faults.call_tool_name:
            return request.faults.call_tool_name, []
        if request.skill == "read-balance":
            return "get_time_off_balance", ["wql_get"]
        action = self.package.orchestration.action_id
        dependencies = [
            name for name in self.package.orchestration.workday_tools if name != action
        ]
        return action, dependencies

    def _store(
        self,
        request: InvokeRequest,
        code: str,
        nodes: list[TraceNode],
        event_id: str | None,
        retry_attempts: int,
        message: str | None = None,
    ) -> Trace:
        self._sequence += 1
        redacted_nodes: list[TraceNode] = []
        for node in nodes:
            inputs = redact_obj(node.inputs)
            outputs = redact_obj(node.outputs)
            assert isinstance(inputs, dict)
            assert isinstance(outputs, dict)
            redacted_nodes.append(
                TraceNode(name=node.name, status=node.status, inputs=inputs, outputs=outputs)
            )
        failure = class_for(code)
        outcome = outcome_for(code)
        trace = Trace(
            trace_id="tr-" + str(self._sequence).zfill(4),
            agent=self.package.agent.name,
            skill=request.skill,
            actor_id=request.actor_id,
            failure_class=failure,
            outcome=outcome,
            code=code,
            runbook_section=section_for(code),
            message=message or _MESSAGES.get(code, code),
            nodes=redacted_nodes,
            business_process_event_id=event_id,
            retry_attempts=retry_attempts,
        )
        self.traces[trace.trace_id] = trace
        return trace

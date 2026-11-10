"""Map a lab reason code to a section of the root-cause runbook."""

from __future__ import annotations

from fde_lab.models import FailureClass, Outcome

SECTIONS: dict[str, str] = {
    "ok": "timeout-retry-idempotency",
    "not_deployed": "tenant-deployment",
    "skill_disabled": "skills",
    "not_in_available_to": "security-groups",
    "unknown_tool": "agent-gateway-mcp",
    "wid_missing": "rest-soap-wql",
    "prompt_tool_missing": "agent-gateway-mcp",
    "domain_denied": "security-groups",
    "outside_management_chain": "security-groups",
    "rest_403": "rest-soap-wql",
    "soap_401": "rest-soap-wql",
    "task_not_authorized": "rest-soap-wql",
    "malformed_input": "malformed-input",
    "schema_mismatch": "malformed-input",
    "timed_out": "timeout-retry-idempotency",
    "retry_exhausted": "timeout-retry-idempotency",
    "insufficient_balance": "timeout-retry-idempotency",
    "response_too_large": "configuration",
    "token_invalid": "tokens",
    "token_stale": "tokens",
    "tenant_alias_missing": "configuration",
    "direct_api_blocked": "agent-gateway-mcp",
    "asor_validation": "asor-registration",
    "asor_unauthorized": "asor-registration",
    "asor_forbidden": "asor-registration",
    "asor_not_found": "asor-registration",
    "ambient_custom_agent": "configuration",
    "employee_on_write": "security-groups",
    "replayed": "timeout-retry-idempotency",
}

CLASS_FOR: dict[str, FailureClass] = {
    "ok": FailureClass.OK,
    "replayed": FailureClass.OK,
    "not_deployed": FailureClass.TENANT_DEPLOYMENT,
    "skill_disabled": FailureClass.CONFIGURATION,
    "not_in_available_to": FailureClass.PERMISSION,
    "unknown_tool": FailureClass.MISSING_TOOL,
    "wid_missing": FailureClass.MISSING_RESOURCE,
    "prompt_tool_missing": FailureClass.MISSING_RESOURCE,
    "domain_denied": FailureClass.PERMISSION,
    "outside_management_chain": FailureClass.PERMISSION,
    "rest_403": FailureClass.PERMISSION,
    "soap_401": FailureClass.PERMISSION,
    "task_not_authorized": FailureClass.PERMISSION,
    "malformed_input": FailureClass.MALFORMED_INPUT,
    "schema_mismatch": FailureClass.MALFORMED_INPUT,
    "timed_out": FailureClass.TIMEOUT,
    "retry_exhausted": FailureClass.RETRY_EXHAUSTED,
    "insufficient_balance": FailureClass.BUSINESS_RULE,
    "response_too_large": FailureClass.CONFIGURATION,
    "token_invalid": FailureClass.AUTHENTICATION,
    "token_stale": FailureClass.AUTHENTICATION,
    "tenant_alias_missing": FailureClass.CONFIGURATION,
    "direct_api_blocked": FailureClass.CONFIGURATION,
    "asor_validation": FailureClass.CONFIGURATION,
    "asor_unauthorized": FailureClass.AUTHENTICATION,
    "asor_forbidden": FailureClass.PERMISSION,
    "asor_not_found": FailureClass.MISSING_RESOURCE,
    "ambient_custom_agent": FailureClass.CONFIGURATION,
    "employee_on_write": FailureClass.CONFIGURATION,
}

OUTCOME_FOR: dict[str, Outcome] = {
    "ok": Outcome.COMPLETED,
    "replayed": Outcome.COMPLETED,
    "not_deployed": Outcome.NOT_LISTED,
    "skill_disabled": Outcome.NOT_LISTED,
    "not_in_available_to": Outcome.NOT_LISTED,
    "timed_out": Outcome.TIMED_OUT,
    "insufficient_balance": Outcome.COMPLETED_WITH_ERRORS,
}


def section_for(code: str) -> str:
    return SECTIONS[code]


def class_for(code: str) -> FailureClass:
    return CLASS_FOR[code]


def outcome_for(code: str) -> Outcome:
    return OUTCOME_FOR.get(code, Outcome.FAILED)

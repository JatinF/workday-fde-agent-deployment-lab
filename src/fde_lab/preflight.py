"""Checks an agent package before anyone points it at a tenant."""

from __future__ import annotations

import re

from fde_lab.asor import build_registration, validate_registration
from fde_lab.models import Finding, LabPackage
from fde_lab.prompts import missing_prompt_tools
from fde_lab.security import security_findings

_WID = re.compile(r"^[0-9a-fA-F]{32}$")
_HEADER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_DOCUMENTED_SYNC_TIMEOUT_MS = 300_000
_DOCUMENTED_RESPONSE_LIMIT = 1_048_576
_EFFECTS = {"Destructive", "Idempotent", "Read-Only", "Open World"}


def preflight(package: LabPackage) -> list[Finding]:
    findings: list[Finding] = []
    if not package.agent.frontmatter_opened:
        findings.append(
            Finding(
                code="frontmatter_open",
                severity="warning",
                message="The .agent file omits the opening frontmatter marker.",
                section="configuration",
            )
        )
    if package.security.version not in package.security.deployed_versions:
        findings.append(
            Finding(
                code="not_deployed",
                severity="error",
                message="The package version is not in deployed_versions.",
                section="tenant-deployment",
            )
        )
    for skill_name in package.agent.skills:
        if skill_name not in package.skills:
            findings.append(
                Finding(
                    code="skill_file_missing",
                    severity="error",
                    message="No .agentskill file for " + skill_name + ".",
                    section="skills",
                )
            )
    for skill in package.skills.values():
        if not skill.frontmatter_opened:
            findings.append(
                Finding(
                    code="frontmatter_open",
                    severity="warning",
                    message=skill.name + " omits the opening frontmatter marker.",
                    section="skills",
                )
            )
        if skill.allowed_tools_form == "string":
            findings.append(
                Finding(
                    code="allowed_tools_string",
                    severity="warning",
                    message=(
                        skill.name
                        + " uses the agentskills.io string form. Workday samples use a list."
                    ),
                    section="skills",
                )
            )
        if not skill.tags:
            findings.append(
                Finding(
                    code="skill_tags_missing",
                    severity="error",
                    message=skill.name + " needs at least one tag for the ASOR skill.",
                    section="asor-registration",
                )
            )
        if not skill.allowed_tools:
            findings.append(
                Finding(
                    code="allowed_tools_empty",
                    severity="error",
                    message=skill.name + " has no allowed-tools.",
                    section="skills",
                )
            )
        for tool_name in skill.allowed_tools:
            tool = package.catalog.tool(tool_name)
            wid = skill.tool_wids.get(tool_name)
            if tool is None:
                findings.append(
                    Finding(
                        code="unknown_tool",
                        severity="error",
                        message=tool_name + " is not in the lab catalog.",
                        section="agent-gateway-mcp",
                    )
                )
                continue
            if wid is None:
                findings.append(
                    Finding(
                        code="wid_missing",
                        severity="error",
                        message=tool_name + " has no tool-wid.",
                        section="rest-soap-wql",
                    )
                )
                continue
            if not _WID.match(wid):
                findings.append(
                    Finding(
                        code="wid_shape",
                        severity="error",
                        message=tool_name + " WID must be 32 hex characters.",
                        section="rest-soap-wql",
                    )
                )
            if wid != tool.wid:
                findings.append(
                    Finding(
                        code="wid_catalog_mismatch",
                        severity="error",
                        message=tool_name + " WID does not match the catalog.",
                        section="rest-soap-wql",
                    )
                )
        for prompt in missing_prompt_tools(skill, package.catalog):
            findings.append(
                Finding(
                    code="prompt_tool_missing",
                    severity="error",
                    message=skill.name + " is missing required prompt tool " + prompt + ".",
                    section="agent-gateway-mcp",
                )
            )
    findings.extend(_orchestration_findings(package))
    findings.extend(security_findings(package))
    registration_errors = validate_registration(build_registration(package))
    for code in registration_errors:
        findings.append(
            Finding(
                code=code,
                severity="error",
                message="ASOR registration failed validation: " + code + ".",
                section="asor-registration",
            )
        )
    return findings


def _orchestration_findings(package: LabPackage) -> list[Finding]:
    action = package.orchestration
    findings: list[Finding] = []
    if len(action.name) > 30:
        findings.append(
            Finding(
                code="action_name_length",
                severity="error",
                message="Custom Agent Action names are limited to 30 characters.",
                section="configuration",
            )
        )
    if action.template != "Custom Agent Action":
        findings.append(
            Finding(
                code="action_template",
                severity="error",
                message="The orchestration template must be Custom Agent Action.",
                section="configuration",
            )
        )
    if action.action_id != action.name:
        findings.append(
            Finding(
                code="action_id_mismatch",
                severity="error",
                message="Call the action by the registered Action ID.",
                section="agent-gateway-mcp",
            )
        )
    if action.effect not in _EFFECTS:
        findings.append(
            Finding(
                code="action_effect",
                severity="error",
                message="Effect must be one of the documented annotation values.",
                section="configuration",
            )
        )
    if action.timeout_ms > _DOCUMENTED_SYNC_TIMEOUT_MS:
        findings.append(
            Finding(
                code="timeout_over_limit",
                severity="error",
                message="Synchronous orchestrations time out at 5 minutes.",
                section="timeout-retry-idempotency",
            )
        )
    if action.response_limit_bytes > _DOCUMENTED_RESPONSE_LIMIT:
        findings.append(
            Finding(
                code="response_limit",
                severity="error",
                message="Described response properties are limited to 1 MB.",
                section="configuration",
            )
        )
    for prop in action.request_properties:
        if not prop.description.strip():
            findings.append(
                Finding(
                    code="property_description",
                    severity="error",
                    message=prop.name + " needs a description, format, and sample.",
                    section="malformed-input",
                )
            )
    if action.query_parameters:
        findings.append(
            Finding(
                code="empty_query_parameter",
                severity="error",
                message="Remove unused query parameter rows before saving.",
                section="malformed-input",
            )
        )
    for header in action.headers:
        if not _HEADER.match(header):
            findings.append(
                Finding(
                    code="header_name",
                    severity="error",
                    message="Header " + header + " uses characters Orchestrate rejects.",
                    section="configuration",
                )
            )
    write_skill = package.skills.get("request-coverage")
    if write_skill is not None and action.action_id not in write_skill.allowed_tools:
        findings.append(
            Finding(
                code="action_not_on_skill",
                severity="error",
                message="The Action ID is not in the skill allowed-tools list.",
                section="skills",
            )
        )
    return findings

"""Least-privilege checks for the shipped custom agent.

Custom Agents are delegate-only. A write skill is refused unless every Available To
group also sits on the domain policy for every write tool in that skill.
"""

from __future__ import annotations

from fde_lab.models import Finding, LabPackage

_WRITE_EFFECTS = {"destructive", "idempotent"}


def _write_domains(package: LabPackage, tool_names: list[str]) -> set[str] | None:
    groups: set[str] | None = None
    for name in tool_names:
        tool = package.catalog.tool(name)
        if tool is None or tool.effect not in _WRITE_EFFECTS:
            continue
        policy = package.catalog.policies.get(tool.domain)
        if policy is None:
            return set()
        current = set(policy.groups)
        groups = current if groups is None else groups & current
    return groups


def security_findings(package: LabPackage) -> list[Finding]:
    findings: list[Finding] = []
    if package.security.execution_mode != "Delegate":
        findings.append(
            Finding(
                code="ambient_custom_agent",
                severity="error",
                message="Custom Agents are delegate mode only.",
                section="configuration",
            )
        )
    if not package.security.asu_groups:
        findings.append(
            Finding(
                code="asu_missing",
                severity="error",
                message="Activation requires a security group so an ASU can be created.",
                section="security-groups",
            )
        )
    for skill_name, skill in package.skills.items():
        security = package.security.skills.get(skill_name)
        if security is None:
            findings.append(
                Finding(
                    code="skill_security_missing",
                    severity="error",
                    message="No Available To list for " + skill_name + ".",
                    section="security-groups",
                )
            )
            continue
        if not security.available_to:
            findings.append(
                Finding(
                    code="available_to_empty",
                    severity="error",
                    message=skill_name + " has an empty Available To list.",
                    section="security-groups",
                )
            )
        allowed = _write_domains(package, skill.allowed_tools)
        if allowed is None:
            continue
        extra = [group for group in security.available_to if group not in allowed]
        if extra:
            findings.append(
                Finding(
                    code=(
                        "employee_on_write"
                        if "SYN-SG-EMPLOYEE" in extra
                        else "available_to_outside_domain"
                    ),
                    severity="error",
                    message=(
                        skill_name
                        + " Available To is outside the write domain: "
                        + ", ".join(extra)
                    ),
                    section="security-groups",
                )
            )
        asu_extra = [group for group in package.security.asu_groups if group not in allowed]
        write_tools = [
            tool
            for name in skill.allowed_tools
            if (tool := package.catalog.tool(name)) is not None and tool.effect in _WRITE_EFFECTS
        ]
        if asu_extra and write_tools:
            findings.append(
                Finding(
                    code="asu_outside_domain",
                    severity="error",
                    message="ASU groups exceed the write domain: " + ", ".join(asu_extra),
                    section="security-groups",
                )
            )
    return findings

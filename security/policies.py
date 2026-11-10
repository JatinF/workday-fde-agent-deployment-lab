"""Compare the security templates with the loaded lab package."""

from __future__ import annotations

from pathlib import Path

import yaml

from fde_lab.load import load_package
from fde_lab.models import LabPackage


def template_findings(root: Path) -> list[str]:
    package = load_package(root)
    findings: list[str] = []
    roles = _mapping(root / "security" / "roles.yaml")
    permissions = _mapping(root / "security" / "permissions.yaml")
    findings.extend(_role_findings(package, roles))
    findings.extend(_domain_findings(package, permissions))
    return findings


def _role_findings(package: LabPackage, roles: dict[str, object]) -> list[str]:
    groups = roles.get("groups")
    if not isinstance(groups, list):
        return ["roles.groups"]
    readers: list[str] = []
    submitters: list[str] = []
    employee_submit = False
    for row in groups:
        if not isinstance(row, dict):
            return ["roles.row"]
        group_id = row.get("id")
        if not isinstance(group_id, str):
            return ["roles.id"]
        if row.get("may_read") is True:
            readers.append(group_id)
        if row.get("may_submit_time_off") is True:
            submitters.append(group_id)
        if group_id == "SYN-SG-EMPLOYEE" and row.get("may_submit_time_off") is True:
            employee_submit = True
    findings: list[str] = []
    read_skill = package.security.skills["read-balance"].available_to
    write_skill = package.security.skills["request-coverage"].available_to
    if readers != read_skill:
        findings.append("roles.read")
    if submitters != write_skill:
        findings.append("roles.write")
    if employee_submit or "SYN-SG-EMPLOYEE" in write_skill:
        findings.append("roles.employee_on_write")
    asu = roles.get("asu")
    if not isinstance(asu, dict):
        return findings + ["roles.asu"]
    asu_groups = asu.get("security_groups")
    if asu.get("name") != package.security.asu_name or asu_groups != package.security.asu_groups:
        findings.append("roles.asu")
    return findings


def _domain_findings(package: LabPackage, permissions: dict[str, object]) -> list[str]:
    domains = permissions.get("domains")
    if not isinstance(domains, dict):
        return ["permissions.domains"]
    findings: list[str] = []
    if set(domains) != set(package.catalog.policies):
        findings.append("permissions.domain_names")
    for name, policy in package.catalog.policies.items():
        raw = domains.get(name)
        if not isinstance(raw, dict) or raw.get("groups") != policy.groups:
            findings.append("permissions." + name)
    excluded = permissions.get("write_excludes")
    write_skill = package.security.skills["request-coverage"].available_to
    if not isinstance(excluded, list) or any(item in write_skill for item in excluded):
        findings.append("permissions.write_excludes")
    return findings


def _mapping(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("expected a mapping at " + str(path))
    parsed: dict[str, object] = {}
    for key, value in loaded.items():
        parsed[str(key)] = value
    return parsed

"""Local Agent Gateway check order.

The published troubleshooting page says a missing deployment, skill, registration,
or Available To membership omits the tool and returns no error. This stand-in records
the reason on the trace and still sets outcome not_listed.
"""

from __future__ import annotations

from fde_lab.models import AccessToken, Faults, LabPackage, PackageSecurity


def effective_security(package: LabPackage, faults: Faults) -> PackageSecurity:
    security = package.security.model_copy(deep=True)
    if faults.undeployed:
        security.deployed_versions = []
    if faults.disable_skill and faults.disable_skill in security.skills:
        security.skills[faults.disable_skill].enabled = False
    return security


def effective_wids(package: LabPackage, skill_name: str, faults: Faults) -> dict[str, str]:
    skill = package.skills[skill_name]
    return {
        name: wid
        for name, wid in skill.tool_wids.items()
        if name not in faults.drop_tool_wids
    }


def authorize_tool(
    package: LabPackage,
    *,
    actor_groups: list[str],
    skill_name: str,
    tool_name: str,
    token: AccessToken,
    faults: Faults,
    tenant_alias: str,
    registration_epoch: int,
) -> str:
    """Return a reason code. `ok` means the tool is listed and executable."""
    if faults.tenant_alias_missing or not tenant_alias:
        return "tenant_alias_missing"
    if faults.direct_api:
        return "direct_api_blocked"
    if not token.valid:
        return "token_invalid"
    if token.issued_epoch < registration_epoch:
        return "token_stale"
    security = effective_security(package, faults)
    if security.version not in security.deployed_versions:
        return "not_deployed"
    skill_security = security.skills.get(skill_name)
    skill = package.skills.get(skill_name)
    if skill_security is None or skill is None:
        return "skill_disabled"
    if not skill_security.enabled:
        return "skill_disabled"
    if not set(actor_groups) & set(skill_security.available_to):
        return "not_in_available_to"
    if tool_name not in skill.allowed_tools:
        return "unknown_tool"
    wids = effective_wids(package, skill_name, faults)
    if tool_name not in wids:
        return "wid_missing"
    tool = package.catalog.tool(tool_name)
    if tool is None:
        return "unknown_tool"
    for prompt in tool.required_prompts:
        if prompt not in wids:
            return "prompt_tool_missing"
    policy = package.catalog.policies.get(tool.domain)
    if policy is None or not set(actor_groups) & set(policy.groups):
        return "domain_denied"
    if tool.protocol == "rest" and faults.rest_status == 403:
        return "rest_403"
    if tool.protocol == "soap" and faults.soap_status == 401:
        return "soap_401"
    return "ok"

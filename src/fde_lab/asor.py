"""Build and check an ASOR v1.2 agent definition. This does not call Workday."""

from __future__ import annotations

from fde_lab.models import AccessToken, LabPackage, LabState

_REQUIRED = (
    "name",
    "description",
    "url",
    "provider",
    "platform",
    "version",
    "capabilities",
    "skills",
)


def build_registration(package: LabPackage) -> dict[str, object]:
    skill_rows: list[dict[str, object]] = []
    config_rows: list[dict[str, object]] = []
    for skill_name in package.agent.skills:
        skill = package.skills[skill_name]
        skill_rows.append(
            {
                "id": skill.name,
                "name": skill.name,
                "description": skill.description,
                "tags": [{"tag": tag} for tag in skill.tags],
                "inputModes": [{"type": "application/json"}],
                "outputModes": [{"type": "application/json"}],
            }
        )
        resources: list[dict[str, object]] = []
        for tool_name, wid in skill.tool_wids.items():
            tool = package.catalog.tool(tool_name)
            description = tool.description if tool is not None else tool_name
            agent_resource: dict[str, object] = {"id": wid}
            if tool is not None and tool.protocol == "orchestration":
                agent_resource["descriptor"] = package.orchestration.display_name
                agent_resource["type"] = "AGENT_ACTION"
            resources.append(
                {
                    "tool_name": tool_name,
                    "description": description,
                    "agent_resource": agent_resource,
                }
            )
        if skill_name == "request-coverage":
            resources.append(
                {
                    "tool_name": "POST https://coverage.lab.invalid/slots",
                    "description": "Lab coverage calendar. No live vendor is called.",
                }
            )
        config_rows.append(
            {
                "skillId": skill.name,
                "executionMode": {"id": "Mode=Delegate"},
                "workdayResources": resources,
            }
        )
    return {
        "name": package.agent.name,
        "description": package.agent.description,
        "url": "https://lab.invalid/agents/time-off-coverage",
        "provider": {"id": "Provider=SELF-BUILT"},
        "platform": {"id": "Platform=OTHER"},
        "version": package.security.version,
        "overview": "Lab agent. Not registered in a Workday tenant.",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "defaultInputModes": [{"type": "application/json"}],
        "defaultOutputModes": [{"type": "application/json"}],
        "skills": skill_rows,
        "workdayConfig": config_rows,
    }


def validate_registration(body: object) -> list[str]:
    if not isinstance(body, dict):
        return ["body_not_object"]
    errors: list[str] = []
    for field in _REQUIRED:
        if field not in body:
            errors.append("missing_" + field)
    provider = body.get("provider")
    platform = body.get("platform")
    if isinstance(provider, dict):
        provider_id = provider.get("id")
        if not isinstance(provider_id, str) or not provider_id.startswith("Provider="):
            errors.append("provider_id")
    elif "provider" in body:
        errors.append("provider_id")
    if isinstance(platform, dict):
        platform_id = platform.get("id")
        if not isinstance(platform_id, str) or not platform_id.startswith("Platform="):
            errors.append("platform_id")
    elif "platform" in body:
        errors.append("platform_id")
    url = body.get("url")
    if isinstance(url, str) and not url.startswith("https://"):
        errors.append("url_scheme")
    skills = body.get("skills")
    if isinstance(skills, list):
        for index, skill in enumerate(skills):
            if not isinstance(skill, dict):
                errors.append("skill_" + str(index))
                continue
            for field in ("id", "name", "description", "tags"):
                if field not in skill:
                    errors.append("skill_" + str(index) + "_missing_" + field)
            tags = skill.get("tags")
            if isinstance(tags, list) and len(tags) == 0:
                errors.append("skill_" + str(index) + "_empty_tags")
    elif "skills" in body:
        errors.append("skills_type")
    config = body.get("workdayConfig")
    if isinstance(config, list):
        for index, row in enumerate(config):
            if not isinstance(row, dict):
                errors.append("workday_config_" + str(index))
                continue
            mode = row.get("executionMode")
            mode_id = mode.get("id") if isinstance(mode, dict) else None
            if mode_id == "Mode=Ambient":
                errors.append("ambient_custom_agent")
            elif mode_id != "Mode=Delegate":
                errors.append("execution_mode_" + str(index))
            resources = row.get("workdayResources")
            if isinstance(resources, list):
                for resource in resources:
                    if isinstance(resource, dict) and "tool_name" not in resource:
                        errors.append("resource_missing_tool_name")
    return errors


class AsorResponse:
    def __init__(self, status: int, code: str, body: dict[str, object]) -> None:
        self.status = status
        self.code = code
        self.body = body


class AsorService:
    """Local stand-in for POST/GET /asor/v1/agentDefinition."""

    def post(
        self,
        body: object,
        token: AccessToken | None,
        domains: set[str],
        state: LabState,
    ) -> AsorResponse:
        if token is None or not token.valid:
            return AsorResponse(401, "asor_unauthorized", {"error": "rejected token"})
        if "Development" not in domains:
            return AsorResponse(403, "asor_forbidden", {"error": "insufficient permissions"})
        errors = validate_registration(body)
        if errors:
            return AsorResponse(
                400,
                "asor_validation",
                {"error": "invalid request", "errors": errors},
            )
        assert isinstance(body, dict)
        provider = body["provider"]
        assert isinstance(provider, dict)
        key = str(body["name"]) + "|" + str(provider["id"]) + "|" + str(body["version"])
        existing_id = ""
        for agent_id, record in state.asor_records.items():
            if record.get("key") == key:
                existing_id = agent_id
                break
        if existing_id:
            state.asor_records[existing_id] = {"key": key, "body": body}
            state.registration_epoch += 1
            return AsorResponse(201, "ok", {"id": existing_id, "updated": True})
        agent_id = "asor-" + str(len(state.asor_records) + 1).zfill(4)
        state.asor_records[agent_id] = {"key": key, "body": body}
        state.registration_epoch += 1
        return AsorResponse(201, "ok", {"id": agent_id, "updated": False})

    def get(
        self,
        agent_id: str,
        token: AccessToken | None,
        domains: set[str],
        state: LabState,
    ) -> AsorResponse:
        if token is None or not token.valid:
            return AsorResponse(401, "asor_unauthorized", {"error": "rejected token"})
        if "Setup: Agents" not in domains:
            return AsorResponse(403, "asor_forbidden", {"error": "insufficient permissions"})
        record = state.asor_records.get(agent_id)
        if record is None:
            return AsorResponse(404, "asor_not_found", {"error": "resource not found"})
        stored = record.get("body")
        payload = dict(stored) if isinstance(stored, dict) else {}
        payload["id"] = agent_id
        return AsorResponse(200, "ok", payload)

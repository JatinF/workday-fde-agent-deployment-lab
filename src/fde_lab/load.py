"""Load the shipped agent package from the repository tree."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from fde_lab.artifacts import parse_agent, parse_skill
from fde_lab.models import (
    Catalog,
    LabPackage,
    Orchestration,
    PackageSecurity,
    PolicyDef,
    PromptValue,
    SkillSecurity,
    TenantData,
    ToolDef,
    Worker,
)
from fde_lab.paths import repo_root


def _mapping(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(path.name + " must be a mapping")
    return {str(key): value for key, value in loaded.items()}


def load_catalog(path: Path) -> Catalog:
    raw = _mapping(path)
    tools_raw = raw.get("tools")
    policies_raw = raw.get("policies")
    prompts_raw = raw.get("prompt_values")
    if not isinstance(tools_raw, list) or not isinstance(policies_raw, dict):
        raise ValueError("catalog tools and policies are malformed")
    if not isinstance(prompts_raw, list):
        raise ValueError("catalog prompt_values are malformed")
    tools = {tool.name: tool for tool in (ToolDef.model_validate(item) for item in tools_raw)}
    policies: dict[str, PolicyDef] = {}
    for name, value in policies_raw.items():
        policies[str(name)] = PolicyDef.model_validate(value)
    prompt_values = {
        item.wid: item for item in (PromptValue.model_validate(row) for row in prompts_raw)
    }
    return Catalog(tools=tools, policies=policies, prompt_values=prompt_values)


def load_tenant(path: Path) -> TenantData:
    raw = _mapping(path)
    org = raw.get("org_id")
    workers_raw = raw.get("workers")
    if not isinstance(org, str) or not isinstance(workers_raw, list):
        raise ValueError("tenant file is malformed")
    workers = {
        worker.worker_id: worker
        for worker in (Worker.model_validate(item) for item in workers_raw)
    }
    return TenantData(org_id=org, workers=workers)


def load_security(path: Path) -> PackageSecurity:
    raw = _mapping(path)
    skills_raw = raw.get("skills")
    asu_raw = raw.get("asu")
    if not isinstance(skills_raw, dict) or not isinstance(asu_raw, dict):
        raise ValueError("security file is malformed")
    skills = {
        str(name): SkillSecurity.model_validate(value) for name, value in skills_raw.items()
    }
    asu_name = asu_raw.get("name")
    asu_groups = asu_raw.get("security_groups")
    if not isinstance(asu_name, str) or not isinstance(asu_groups, list):
        raise ValueError("asu block is malformed")
    groups = [group for group in asu_groups if isinstance(group, str)]
    deployed = raw.get("deployed_versions")
    if not isinstance(deployed, list):
        raise ValueError("deployed_versions must be a list")
    versions = [item for item in deployed if isinstance(item, str)]
    execution_mode = raw.get("execution_mode")
    app_id = raw.get("app_id")
    version = raw.get("version")
    if not isinstance(execution_mode, str) or not isinstance(app_id, str):
        raise ValueError("security identity fields are malformed")
    if not isinstance(version, str):
        raise ValueError("version must be a string")
    return PackageSecurity(
        execution_mode=execution_mode,
        app_id=app_id,
        version=version,
        deployed_versions=versions,
        skills=skills,
        asu_name=asu_name,
        asu_groups=groups,
    )


def load_package(root: Path | None = None) -> LabPackage:
    base = root or repo_root()
    agent_dir = base / "agent" / "time-off-coverage"
    agent = parse_agent(agent_dir / "time-off-coverage.agent")
    skills = {
        skill.name: skill
        for skill in (
            parse_skill(path) for path in sorted(agent_dir.glob("*.agentskill"))
        )
    }
    orchestration_path = agent_dir / "orchestrations" / "request-coverage.json"
    orchestration = Orchestration.model_validate(
        json.loads(orchestration_path.read_text(encoding="utf-8"))
    )
    return LabPackage(
        agent=agent,
        skills=skills,
        security=load_security(agent_dir / "security" / "groups.yaml"),
        orchestration=orchestration,
        catalog=load_catalog(base / "fixtures" / "catalog.yaml"),
        tenant=load_tenant(base / "fixtures" / "tenant.yaml"),
    )

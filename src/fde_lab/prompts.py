"""Reusable prompt-tool check extracted from a registration failure."""

from __future__ import annotations

from fde_lab.models import Catalog, SkillArtifact


def missing_prompt_tools(skill: SkillArtifact, catalog: Catalog) -> list[str]:
    """Return prompt tools a write tool requires and the skill does not register."""
    missing: list[str] = []
    for tool_name in skill.allowed_tools:
        tool = catalog.tool(tool_name)
        if tool is None:
            continue
        for prompt in tool.required_prompts:
            registered = prompt in skill.allowed_tools and prompt in skill.tool_wids
            if not registered and prompt not in missing:
                missing.append(prompt)
    return missing


def attach_required_prompts(skill: SkillArtifact, catalog: Catalog) -> SkillArtifact:
    """Add each required prompt tool to allowed-tools and tool-wids."""
    tools = list(skill.allowed_tools)
    wids = dict(skill.tool_wids)
    for tool_name in list(tools):
        tool = catalog.tool(tool_name)
        if tool is None:
            continue
        for prompt in tool.required_prompts:
            prompt_tool = catalog.tool(prompt)
            if prompt_tool is None:
                continue
            if prompt not in tools:
                tools.append(prompt)
            wids.setdefault(prompt, prompt_tool.wid)
    return skill.model_copy(update={"allowed_tools": tools, "tool_wids": wids})

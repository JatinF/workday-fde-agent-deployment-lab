"""Parse .agent and .agentskill files.

Workday's sample .agent omits the opening frontmatter marker. This parser accepts
that form and the agentskills.io form that opens with ---.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml

from fde_lab.models import AgentArtifact, SkillArtifact


def split_frontmatter(text: str) -> tuple[dict[str, object], str, bool]:
    lines = text.splitlines()
    if not lines:
        raise ValueError("artifact is empty")
    opened = lines[0].strip() == "---"
    start = 1 if opened else 0
    end: int | None = None
    for index in range(start, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise ValueError("artifact is missing the closing frontmatter marker")
    loaded = yaml.safe_load("\n".join(lines[start:end]))
    if not isinstance(loaded, dict):
        raise ValueError("artifact frontmatter must be a mapping")
    body = "\n".join(lines[end + 1 :]).strip()
    mapping = {str(key): value for key, value in loaded.items()}
    return mapping, body, opened


def _text(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key, "")
    if not isinstance(value, str):
        raise ValueError(key + " must be a string")
    return value.strip()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("expected a list of strings")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("expected a list of strings")
        items.append(item)
    return items


def parse_agent(path: Path) -> AgentArtifact:
    mapping, body, opened = split_frontmatter(path.read_text(encoding="utf-8"))
    return AgentArtifact(
        name=_text(mapping, "name"),
        description=_text(mapping, "description"),
        skills=_string_list(mapping.get("skills")),
        body=body,
        frontmatter_opened=opened,
    )


def _allowed_tools(value: object) -> tuple[list[str], Literal["list", "string"]]:
    if isinstance(value, str):
        return [part for part in value.split() if part], "string"
    return _string_list(value), "list"


def _tool_wids(value: object) -> dict[str, str]:
    if not isinstance(value, list):
        raise ValueError("tool-wids must be a list")
    found: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("tool-wids entries must be mappings")
        name = item.get("name")
        wid = item.get("wid")
        if not isinstance(name, str) or not isinstance(wid, str):
            raise ValueError("tool-wids name and wid must be strings")
        found[name] = wid
    return found


def _tags(mapping: dict[str, object]) -> list[str]:
    metadata = mapping.get("metadata")
    if not isinstance(metadata, dict):
        return []
    tags = metadata.get("tags")
    if tags is None:
        return []
    return _string_list(tags)


def parse_skill(path: Path) -> SkillArtifact:
    mapping, body, opened = split_frontmatter(path.read_text(encoding="utf-8"))
    allowed, form = _allowed_tools(mapping.get("allowed-tools"))
    return SkillArtifact(
        name=_text(mapping, "name"),
        description=_text(mapping, "description"),
        tags=_tags(mapping),
        allowed_tools=allowed,
        tool_wids=_tool_wids(mapping.get("tool-wids")),
        body=body,
        allowed_tools_form=form,
        frontmatter_opened=opened,
    )

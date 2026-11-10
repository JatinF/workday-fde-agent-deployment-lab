from __future__ import annotations

from fde_lab.artifacts import split_frontmatter
from fde_lab.asor import build_registration, validate_registration
from fde_lab.gates import development_tenant_gate
from fde_lab.load import load_package
from fde_lab.preflight import preflight
from fde_lab.prompts import attach_required_prompts


def test_shipped_package_passes_preflight() -> None:
    findings = [item for item in preflight(load_package()) if item.severity == "error"]
    assert findings == []


def test_registration_is_delegate_and_local() -> None:
    body = build_registration(load_package())
    assert validate_registration(body) == []
    assert body["url"] == "https://lab.invalid/agents/time-off-coverage"
    config = body["workdayConfig"]
    assert isinstance(config, list)
    for row in config:
        assert isinstance(row, dict)
        mode = row["executionMode"]
        assert isinstance(mode, dict)
        assert mode["id"] == "Mode=Delegate"


def test_documented_wql_method_ids() -> None:
    catalog = load_package().catalog
    assert catalog.tool("wql_get") is not None
    assert catalog.tool("wql_post") is not None
    wql_get = catalog.tool("wql_get")
    wql_post = catalog.tool("wql_post")
    assert wql_get is not None and wql_get.wid == "9749ba9ac47e1000073fdc1bc8a5001a"
    assert wql_post is not None and wql_post.wid == "3e15b2a1676d10000c9572ea9cc264b3"


def test_frontmatter_without_opening_marker() -> None:
    mapping, body, opened = split_frontmatter("name: sample\nskills:\n  - one\n---\n# Prompt\n")
    assert opened is False
    assert mapping["name"] == "sample"
    assert "Prompt" in body


def test_attach_required_prompts_is_idempotent() -> None:
    package = load_package()
    skill = package.skills["request-coverage"]
    repaired = attach_required_prompts(skill, package.catalog)
    assert repaired.tool_wids["list_time_off_types"] == skill.tool_wids["list_time_off_types"]


def test_tenant_gate_does_not_echo_a_token() -> None:
    empty = development_tenant_gate({})
    assert empty.status == "not-run"
    blocked = development_tenant_gate(
        {"WORKDAY_TENANT_ALIAS": "lab-tenant", "WORKDAY_ACCESS_TOKEN": "super-secret-token"}
    )
    assert blocked.status == "blocked"
    assert "super-secret-token" not in blocked.reason

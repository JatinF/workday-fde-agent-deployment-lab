"""Record what this lab did not execute against Workday."""

from __future__ import annotations

import os
from collections.abc import Mapping

from fde_lab.models import Gate


def development_tenant_gate(env: Mapping[str, str] | None = None) -> Gate:
    source = env if env is not None else os.environ
    alias = source.get("WORKDAY_TENANT_ALIAS", "").strip()
    token = source.get("WORKDAY_ACCESS_TOKEN", "").strip()
    if alias and token:
        return Gate(
            name="development-tenant",
            status="blocked",
            reason="A tenant alias and access token are set. This lab does not send them.",
        )
    return Gate(
        name="development-tenant",
        status="not-run",
        reason="WORKDAY_TENANT_ALIAS and WORKDAY_ACCESS_TOKEN are unset. No tenant was requested.",
    )


def static_gates() -> list[Gate]:
    reasons = {
        "app-builder-deploy": "App Builder and App Hub were not opened.",
        "asor-live-post": "POST https://us.agent.workday.com/asor/v1/agentDefinition was not sent.",
        "agent-gateway-live": "No MCP call was made to an Agent Gateway host.",
        "sana": "The agent was not opened in Sana.",
        "orchestrate-builder-export": "No Orchestration Builder export was pulled from a tenant.",
        "docker-local": "Docker is not installed on this workstation.",
        "hosted-llm": "No model was called. Tokens are 0 and no price is applied.",
    }
    return [Gate(name=name, status="not-run", reason=reason) for name, reason in reasons.items()]


def all_gates(env: Mapping[str, str] | None = None) -> list[Gate]:
    return [development_tenant_gate(env), *static_gates()]

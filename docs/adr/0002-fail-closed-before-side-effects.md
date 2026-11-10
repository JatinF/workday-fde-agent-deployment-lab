# ADR 0002: Fail closed before side effects

Status: accepted. Date: 2026-11-09.

The gateway checks the alias, the token, the deploy, the skill, Available To, the tool, the WID, and the domain before the action runs. The business-process authorization fault is checked before the coverage call, so a denied task does not reserve a slot. The Request Time Off row is written only after coverage succeeds. A timeout or an exhausted dependency leaves no event.

That order is a lab choice. It is not an Orchestration Builder export.

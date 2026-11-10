# ADR 0003: Prompt-tool check

Status: accepted. Date: 2026-11-09.

A write tool in the catalog can name required prompt tools. Preflight fails when the skill omits one. `attach_required_prompts` copies the catalog WID back onto the skill. Backlog FDE-BACKLOG-001 is that check. The story is the acceptance run.

The check was encoded from the public prompt-tool rule. It was not taken from a customer tenant.

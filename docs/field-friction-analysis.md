# Field friction analysis

This is the lifecycle for one lab reproduction. No customer was interviewed. No Workday tenant was opened. The documentation contradictions themselves are listed in [field-friction.md](field-friction.md).

## Field issue

The write skill can be saved without `list_time_off_types`. The action id still looks complete. At runtime the gateway returns `prompt_tool_missing` and does not submit Request Time Off. Workday's agent-ready write tools can require prompt tools. The lab catalog encodes that requirement for `request_time_off` and `requestTimeOffCoverage`.

The story reproduces it by deleting the prompt tool from a copy of the package. The measured before-code is `prompt_tool_missing`.

## Engineering backlog

[FDE-BACKLOG-001](backlog/FDE-BACKLOG-001.md) asks for a check that runs before anyone points the package at a tenant.

## Productized solution

`missing_prompt_tools` runs in preflight. `attach_required_prompts` adds the catalog name and WID. The story then invokes the repaired package and requires one successful Request Time Off event. The shipped package still has zero preflight errors.

## What the lifecycle does not close

The fix is a local check. It was not applied in App Builder, ASOR, or a tenant security policy. Those gates stay not-run. The production decision stays NO-GO.

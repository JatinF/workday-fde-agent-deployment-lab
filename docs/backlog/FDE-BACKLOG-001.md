# FDE-BACKLOG-001

Reject a write skill that omits a required prompt tool, and restore the tool from the catalog.

## Source

Lab reproduction of the prompt-tool rule. Not a customer incident. The measured run is the lifecycle section of `reports/field_story.md`.

## Acceptance

- Preflight on the broken copy includes `prompt_tool_missing`.
- `attach_required_prompts` removes the preflight errors.
- The repaired package submits one Request Time Off event.
- The shipped package stays free of preflight errors.

`fde-lab run-story` is the acceptance run. It does not register the agent in Workday.

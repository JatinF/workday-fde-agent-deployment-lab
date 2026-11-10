# Prompt tools as a reusable check

## The failure

Workday's agent-ready write tools can require prompt tools. The coverage action requires `list_time_off_types`. If that name is removed from `allowed-tools` or from `tool-wids`, the skill still parses, and a casual reading of the action id looks complete. At runtime the gateway returns `prompt_tool_missing` and does not submit Request Time Off.

The suite case `prompt-wid-missing` is that failure. It was produced by deleting the prompt registration in a copy of the package. It was not observed in a customer tenant.

## The fix

`attach_required_prompts` in `src/fde_lab/prompts.py` walks every allowed tool, reads `required_prompts` from the catalog, and adds each missing prompt tool's name and catalog WID.

## The reusable check

`missing_prompt_tools` is called from preflight for every skill. A package that drops the prompt tool fails closed before anyone points it at a tenant. The suite case `prompt-tool-fix` removes the prompt tool, asserts the finding, runs `attach_required_prompts`, and asserts the error findings are gone.

The catalog is the source of which prompt a write requires. The skill file has to match it. A WID that does not match the catalog fails with `wid_catalog_mismatch`.

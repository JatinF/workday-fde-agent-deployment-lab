# Field friction

The lifecycle from one lab reproduction to a reusable check is [field-friction-analysis.md](field-friction-analysis.md). The items below are documentation contradictions. They were not observed in a tenant.

These are differences and traps found while building the lab from Workday's public docs. They are not production incidents. No tenant was available to confirm them at runtime.

## 1. No development tenant was obtained

The Open Developer Platform personal-account page says a developer requests one development tenant from Console, Tenants, and signs in as `lmcneil`. The tenant expires after 7 days without a login. This lab does not have an account, a tenant alias, or a token. The gate is not-run. A token found in the environment is not sent.

Source: [Create and Manage Personal Account Development Tenants](https://developer.workday.com/doc/GUID-4f875963-a845-43b5-868a-0f77e6261eb7-enHYPHENus.md).

## 2. The sample `.agent` file omits the opening marker

Workday's sample artifacts open the skill files with `---`. The sample `.agent` file starts at `name:` and only later has a closing `---`. The lab parser accepts both. Preflight warns with `frontmatter_open` when the opening marker is missing. The shipped file includes it.

Source: [Sample Artifacts](https://developer.workday.com/doc/GUID-7e74bb3c-7459-4516-bda7-abe03b7aa456-enHYPHENus.md).

## 3. `allowed-tools` is a list here and a string in the open spec

agentskills.io defines `allowed-tools` as a space-delimited string and marks it experimental. Workday's samples use a YAML list plus a `tool-wids` list of names and WIDs. The lab accepts both. A string form is a warning, `allowed_tools_string`. The shipped skills use the list form.

Sources: [Custom Agents](https://developer.workday.com/doc/GUID-c3910467-0fd6-4f27-b78e-436cfe0a3147-enHYPHENus.md), [Agent Skills specification](https://agentskills.io/specification).

## 4. Four runtime clients, two names

The custom-agent page says every call goes through one of four clients, then names the MCP client and the Custom Agent Actions client. The lab implements those two and rejects anything else. It does not guess the missing names.

## 5. App Hub says plain XML, the samples are YAML

The same custom-agent page says App Hub stores artifacts in plain XML, and the sample topic shows YAML frontmatter with Markdown. This repo keeps the YAML samples. It does not invent an XML wrapper.

## 6. ASU token versus run-as-user

The custom-agent page says tool calls run under the Agent System User token, and that a user can invoke an agent that does things they cannot do personally. The Custom Agent Action troubleshooting page says each step runs as the signed-in user, and that registering a resource does not grant access. The lab fails closed. A call needs the registration, Available To membership, and domain-policy membership. The ASU group is still required in the package so activation has a group to bind. This does not resolve the documentation difference.

Sources: [Custom Agents](https://developer.workday.com/doc/GUID-c3910467-0fd6-4f27-b78e-436cfe0a3147-enHYPHENus.md), [Troubleshoot Custom Agent Actions](https://developer.workday.com/doc/GUID-71867a63-18bd-4b95-802c-2dc3cf90a3d1-enHYPHENus.md).

## 7. A missing tool is omitted with no error

If the app is not deployed, the skill is disabled, the action id is not registered, or the user is outside Available To, the troubleshooting page says the MCP client does not list the action and no error is returned. The lab trace records the reason and sets outcome `not_listed`. The caller does not get a tool error string for those three cases.

## 8. A token from before the registration change is stale

The troubleshooting page says an access token issued before a registration change does not include the new resources, and that the caller must sign in again. The lab bumps `registration_epoch` on an ASOR update and rejects an older token with `token_stale`.

## 9. Prompt tools are part of the write registration

Agent-ready write tools can require prompt tools, and those prompt WIDs have to be in the agent definition. Dropping `list_time_off_types` fails the coverage action with `prompt_tool_missing`. `attach_required_prompts` puts the prompt tool back. That function is the reusable fix. See [prompt tools](capabilities/prompt-tools.md).

Source: [Agent-Ready MCP Prompt Tools](https://developer.workday.com/doc/GUID-bd1ec8d8-7bcf-40d9-a58a-aa805282ebe7-enHYPHENus.md).

## 10. Synchronous timeout and response size

The troubleshooting table says a synchronous orchestration times out at 5 minutes, and a response can fail at 2 MB, or at 1 MB when response-property descriptions are entered. The shipped action uses 300000 ms and 1048576 bytes because every request and response property has a description. The suite's timeout and `response_too_large` cases exercise those limits without allocating a megabyte. The size case compares a declared byte count with the limit.

## 11. Published 401 text does not say unauthenticated

ASOR v1.2 lists 401 as "Invalid resource or operation" and 403 as insufficient permissions. The lab uses 401 when the bearer token is missing or unknown, and 403 when the domain is missing. A live tenant was not called, so this mapping is unconfirmed.

Source: [ASOR v1.2](https://github.com/Workday/asor/blob/main/versions/v1.2.md).

## 12. Custom agents are delegate-only

The custom-agent overview says custom agents are delegate mode only. The external-agent API also allows `Mode=Ambient`. The builder emits `Mode=Delegate`. Preflight rejects `execution_mode: Ambient` on this package.

## 13. WQL method IDs are fixed published values

GET WQL is `9749ba9ac47e1000073fdc1bc8a5001a`. POST WQL is `3e15b2a1676d10000c9572ea9cc264b3`. The read skill registers the GET id. Removing it fails the read even if the balance tool itself is registered, because the skill declared both.

## 14. Empty query-parameter rows

The Custom Agent Action configuration page says an unused query-parameter row can produce an invalid tool schema. The shipped action has an empty query-parameter list. Preflight fails if a row is added. Header names are limited to letters, numbers, hyphens, and underscores, up to 64 characters.

Source: [Configure Custom Agent Action Orchestrations](https://developer.workday.com/doc/GUID-79440bdf-bfe9-44c5-9dde-03ab6f0a6f9d-enHYPHENus.md).

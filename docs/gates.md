# Gates

`fde-lab gates` prints the same list the suite stores.

| Gate | Status | Meaning |
| --- | --- | --- |
| development-tenant | not-run | Both `WORKDAY_TENANT_ALIAS` and `WORKDAY_ACCESS_TOKEN` are unset. If both are set, the status is blocked and the values are not printed or sent. |
| app-builder-deploy | not-run | App Builder and App Hub were not used. |
| asor-live-post | not-run | No request was sent to the Agent Gateway ASOR host. |
| agent-gateway-live | not-run | No MCP session was opened. |
| sana | not-run | The agent was not opened in Sana. |
| orchestrate-builder-export | not-run | The JSON action file is a lab model, not a Builder export. |
| docker-local | not-run | Docker is not installed on this workstation. |
| hosted-llm | not-run | No model was called. |

Passing a local suite does not change these statuses.

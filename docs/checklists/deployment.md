# Deployment checklist

Status is for this repository on the day it was built. "Met in lab" means the local stand-in enforces the check. It does not mean a tenant deployment happened.

| Step | Status | Evidence |
| --- | --- | --- |
| Request one personal development tenant | Not run | `development-tenant` gate. No alias, no login as `lmcneil`. |
| Create an Agent app in App Builder | Not run | Artifacts are files in git. App Builder was not opened. Agent apps cannot include PMD or Model components. This package has neither. |
| Author `.agent` and `.agentskill` | Met in lab | `agent/time-off-coverage/`. Preflight exits 0. |
| Register prompt-tool WIDs with the write | Met in lab | `prompt-wid-missing` fails. `prompt-tool-fix` puts the tool back. |
| Build the Custom Agent Action | Met in lab | Name `requestTimeOffCoverage`, 22 characters, effect Idempotent, descriptions on every property, no empty query row. |
| Deploy the app version to the tenant | Not run | The fixture lists version `0.1.0` as deployed. `tenant-not-deployed` shows the failure when it is not. |
| Confirm ASOR registration in a dev tenant | Not run | Dev environments register on deploy, per the custom-agent page. Live registration was not observed. The local service can store the body. |
| Configure security and activate | Not run | Groups are in `security/groups.yaml`. Agent Management Hub was not opened. The ASU was not created by Workday. |
| Higher environment through App Manager | Not run | Required before a non-dev tenant. No higher environment exists here. |
| Invoke from Workday chat, Sana, a business process, A2A, or MCP | Not run | The lab invoke is a local function call. |
| Read Agent Traces in App Hub | Not run | Local traces are in the API. They are not the 30-day App Hub trace store. |

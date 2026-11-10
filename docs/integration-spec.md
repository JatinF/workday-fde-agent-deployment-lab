# Integration specification

SYN-ENGAGE-TIMEOFF-001. Every endpoint below is the lab stand-in unless the status says not-run.

## Systems

| System | Lab stand-in | Live status |
| --- | --- | --- |
| Agent app artifacts | `.agent`, `.agentskill` | App Hub deploy not-run |
| ASOR | `AsorService` on `POST /asor/agentDefinition` | `https://us.agent.workday.com/asor/v1/agentDefinition` not-run |
| Agent Gateway | `authorize_tool` | `https://{region}/{tenant}/mcp` not-run |
| Orchestrate action | `run_coverage` | Builder export not-run |
| Request Time Off | in-memory event | tenant business process not-run |
| Coverage calendar | counter plus retry | `coverage.lab.invalid` is not a real host |
| Token service | `TokenBook` | OAuth token endpoint not-run |

## Artifacts

The agent file lists `read-balance` and `request-coverage`. Each skill has `allowed-tools` as a YAML list and `tool-wids` entries whose WIDs are 32 hex characters. Fixture WIDs use the `fde0` prefix. The two WQL method IDs are the ones published on Workday's Troubleshoot Custom Agent Actions page: `9749ba9ac47e1000073fdc1bc8a5001a` for GET and `3e15b2a1676d10000c9572ea9cc264b3` for POST. The POST id is in the catalog and is not used by the shipped skills.

## ASOR body

Required by the published v1.2 model and set by the builder: `name`, `description`, `url`, `provider.id` (`Provider=SELF-BUILT`), `platform.id` (`Platform=OTHER`), `version`, `capabilities`, and `skills` with `id`, `name`, `description`, and at least one tag. Each `workdayConfig` row uses `Mode=Delegate`. Orchestration resources add `type: AGENT_ACTION`. The coverage URL is a resource with `tool_name` and no `agent_resource`.

The local service returns 400 for a body that fails those checks, 401 for a missing token, 403 when the caller lacks `Development` on POST or `Setup: Agents` on GET, and 404 for an unknown id. The published v1.2 table describes 401 as "Invalid resource or operation." This lab uses 401 for a rejected token. That difference is recorded in the field-friction report.

A repeated POST with the same name, provider, and version updates the stored agent and increments `registration_epoch`. A token issued earlier fails with `token_stale`.

## Security

| Skill | Available To | Write domain |
| --- | --- | --- |
| read-balance | SYN-SG-MANAGER, SYN-SG-HR-PARTNER | none |
| request-coverage | SYN-SG-MANAGER | time-off-submit, which contains only SYN-SG-MANAGER |

The ASU is named `time-off-coverage` and is in SYN-SG-MANAGER. Activation in a real tenant would create that ASU. Here the group is configuration only. `SYN-SG-EMPLOYEE` on the write skill fails preflight with `employee_on_write`.

Tool execution still requires the actor's groups to sit on the tool's domain policy. Registration alone does not grant that. A manager who is not the worker's manager fails with `outside_management_chain`. That chain check is the lab stand-in for a supervisory-org constraint. It is not a Workday security report.

## Action contract

| Property | Required | Sample |
| --- | --- | --- |
| worker_id | yes | SYN-USER-IVAN |
| hours | yes | 8 |
| time_off_type_wid | yes | fde00000000000000000000000000031 |
| client_request_id | yes | req-1 |
| coverage_note | no | Desk coverage |

Effect annotation: Idempotent. Synchronous timeout: 300000 ms, the documented 5-minute limit. Response descriptions are present, so the lab limit is 1048576 bytes, the documented 1 MB limit when response properties are described. Retry: 3 attempts, only around the coverage call, on 503. The business-process write is stored under `actor|worker|client_request_id`.

Headers on the local ASOR routes: `Authorization: Bearer <lab token>`, `x-lab-domains`, and `wd-agent-tenant-alias`. The alias header is the one Workday documents. `x-lab-domains` exists only because this process has no real security domains.

## Error mapping

| Condition | Class | Listed |
| --- | --- | --- |
| Version not deployed, skill disabled, or actor outside Available To | tenant, configuration, or permission | no |
| Name not registered | missing_tool | the call fails with Unknown tool |
| WID or prompt WID absent | missing_resource | the call fails |
| REST 403, SOAP 401, or task not authorized | permission_failure | the call fails |
| Input schema miss | malformed_input | the call fails |
| Coverage still failing after 3 attempts | retry_exhausted | the call fails |
| Clock past 300000 ms | timeout | the call fails |
| Hours above the balance | business_rule | the action completes with errors and writes no event |

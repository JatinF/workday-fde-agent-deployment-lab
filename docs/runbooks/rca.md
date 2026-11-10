# Root-cause runbook

Use the trace `code` and open the matching section. The suite in `reports/suite_results.md` is the local proof that each code fires. None of these cases were observed in a Workday tenant.

## tenant-deployment

Code: `not_deployed`.

The app version is not in the deployed set, so the tool is not listed and no tool error is returned. On a tenant, confirm the promotion that contains the action is deployed to the tenant in the MCP endpoint, then validate the orchestration. In this lab, `faults.undeployed` clears `deployed_versions`.

## asor-registration

Codes: `asor_validation`, `asor_unauthorized`, `asor_forbidden`, `asor_not_found`.

Check the body against ASOR v1.2 before sending it. POST requires the Development domain. GET requires Setup: Agents. A missing id is 404. The same name, provider, and version updates the existing row. After an update, discard tokens issued at the previous epoch.

The lab does not POST to `https://us.agent.workday.com/asor/v1/agentDefinition`.

## skills

Code: `skill_disabled`.

A disabled or unknown skill is not listed. Confirm the skill file is named in the `.agent` file, `enabled` is true, and the Action ID in the skill is the orchestration's Action ID. Another name for the same action is not accepted.

## security-groups

Codes: `not_in_available_to`, `domain_denied`, `outside_management_chain`, `employee_on_write`.

Available To controls who can see the skill. The domain policy controls who can run the tool. Both have to pass. Adding SYN-SG-EMPLOYEE to the write skill fails preflight. A manager reading or booking a worker outside their chain fails even when the group check passes. HR can read and cannot start the write skill.

On a tenant, open View Security for Agent Skill and look for Review Required or Config Required, then activate pending security policy changes. That report was not opened here.

## rest-soap-wql

Codes: `wid_missing`, `rest_403`, `soap_401`, `task_not_authorized`.

If Orchestration Builder can run the step and the agent call returns REST 403, SOAP 401, or "The task submitted is not authorized," the resource is often missing from the registration, or the user is missing from the domain policy. Register the WID, then sign in again. WQL GET and POST use the published method IDs in the catalog. Copy every WID when several resources share a name. This lab does not call Agent Resource Search.

## agent-gateway-mcp

Codes: `unknown_tool`, `prompt_tool_missing`, `direct_api_blocked`.

`Unknown tool` means the called name is not the registered name. Some clients rewrite `/` to `_`. This action has no slash. A write without its prompt tool fails before the business process. A direct API call never leaves the runtime.

The live MCP URL shape is `https://{agentGatewayRegionEndpoint}/{tenantName}/mcp`. It was not called.

## malformed-input

Code: `malformed_input`.

The action rejects a missing field, a wrong type, an unknown worker, or a time-off type that is not a prompt value. The troubleshooting table says this is the message "The input arguments do not match the expected input schema." Every request property on the shipped action has a description and a sample.

## timeout-retry-idempotency

Codes: `ok`, `replayed`, `timed_out`, `retry_exhausted`, `insufficient_balance`.

A completed read or write uses `ok`. A repeated `client_request_id` uses `replayed` and does not create a second event. The coverage call retries on 503 up to 3 times. The business-process submit does not. Past 300000 ms the outcome is `timed_out`. Hours above the balance finish as `completed_with_errors` and write no event. That last case is a business rule, not a platform fault.

## tokens

Codes: `token_invalid`, `token_stale`.

Reject a missing bearer token. Reject a token whose epoch is older than the registration. Do not write the secret into the trace. The suite case `secret-redacted` injects a bearer string into a tool body and asserts the stored trace has no `lab-token-` value.

Workday's Agent Gateway token URL was not called. Access tokens on the configuration page expire after about an hour. This lab does not refresh one.

## configuration

Codes: `tenant_alias_missing`, `response_too_large`, `ambient_custom_agent`, `direct_api_blocked` is classified with the gateway section.

Send `wd-agent-tenant-alias` on every Agent Gateway request. Keep described responses within 1 MB. Keep this custom agent in Delegate mode.

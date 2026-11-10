# Troubleshooting suite

Local stand-in only. No Workday tenant was called.

| Field | Value |
| --- | --- |
| Cases | 34 |
| Passed | 34 |
| Failed | 0 |
| Token leak count | 0 |
| Business process events after replay | 1 |
| External calls after replay | 1 |
| Suite duration ms | 3.3394 |

| Case | Class | Outcome | Passed | Runbook |
| --- | --- | --- | --- | --- |
| happy-read | ok | completed | True | timeout-retry-idempotency |
| hr-read | ok | completed | True | timeout-retry-idempotency |
| outside-org | permission_failure | failed | True | security-groups |
| happy-write | ok | completed | True | timeout-retry-idempotency |
| replay-write | ok | completed | True | timeout-retry-idempotency |
| write-outside-org | permission_failure | failed | True | security-groups |
| insufficient-balance | business_rule | completed_with_errors | True | timeout-retry-idempotency |
| tenant-not-deployed | tenant_deployment | not_listed | True | tenant-deployment |
| skill-disabled | configuration_error | not_listed | True | skills |
| user-not-in-group | permission_failure | not_listed | True | security-groups |
| hr-write-hidden | permission_failure | not_listed | True | security-groups |
| unknown-tool | missing_tool | failed | True | agent-gateway-mcp |
| wid-missing | missing_resource | failed | True | rest-soap-wql |
| prompt-wid-missing | missing_resource | failed | True | agent-gateway-mcp |
| malformed-input | malformed_input | failed | True | malformed-input |
| rest-403 | permission_failure | failed | True | rest-soap-wql |
| soap-401 | permission_failure | failed | True | rest-soap-wql |
| bp-not-authorized | permission_failure | failed | True | rest-soap-wql |
| timeout | timeout | timed_out | True | timeout-retry-idempotency |
| retry-then-success | ok | completed | True | timeout-retry-idempotency |
| retry-exhausted | retry_exhausted | failed | True | timeout-retry-idempotency |
| stale-token | authentication | failed | True | tokens |
| missing-tenant-alias | configuration_error | failed | True | configuration |
| direct-api-blocked | configuration_error | failed | True | agent-gateway-mcp |
| response-too-large | configuration_error | failed | True | configuration |
| secret-redacted | ok | completed | True | timeout-retry-idempotency |
| asor-400 | configuration_error | failed | True | asor-registration |
| asor-401 | authentication | failed | True | asor-registration |
| asor-403 | permission_failure | failed | True | asor-registration |
| asor-404 | missing_resource | failed | True | asor-registration |
| asor-update | ok | completed | True | asor-registration |
| prompt-tool-fix | ok | completed | True | agent-gateway-mcp |
| employee-on-write | configuration_error | completed | True | security-groups |
| ambient-custom-agent | configuration_error | completed | True | configuration |

## Gates

- development-tenant: not-run
- app-builder-deploy: not-run
- asor-live-post: not-run
- agent-gateway-live: not-run
- sana: not-run
- orchestrate-builder-export: not-run
- docker-local: not-run
- hosted-llm: not-run

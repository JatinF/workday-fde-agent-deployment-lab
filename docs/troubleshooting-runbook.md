# Troubleshooting runbook

Use this for the field story. The code-to-section map for the wider suite is [runbooks/rca.md](runbooks/rca.md). None of these cases were observed in a Workday tenant.

## Procedure

1. Read the trace `code` and the node list.
2. Open the matching section in [runbooks/rca.md](runbooks/rca.md).
3. Read Symptom, Telemetry, Diagnosis, Root cause, Fix, Validation, and Prevention for that scenario in `reports/field_story.md`.
4. Apply the fix in a fresh process. The Validation line is the lab's re-run.
5. Leave every production gate at its current status. A local validation does not activate a security policy or register an agent.

## Scenario index

| Scenario | Code | What the re-run shows |
| --- | --- | --- |
| authentication_401 | token_invalid | ASOR stand-in returns 401, then 201 with a new lab token |
| authorization_403 | rest_403 | The shipped write succeeds when the 403 is not injected |
| missing_permission | not_in_available_to | HR can read and still cannot write |
| invalid_configuration | tenant_alias_missing | The shipped alias passes |
| schema_mismatch | schema_mismatch | An integer hour succeeds |
| malformed_payload | malformed_input | A client_request_id succeeds |
| timeout | timed_out | A call inside the limit succeeds |
| duplicate_request | replayed | One event and one external call |
| dependency_failure | retry_exhausted | Attempt 3 succeeds after two failures |
| configuration_drift | token_stale | A token at the current epoch succeeds |

`fde-lab run-story` fails if a scenario code changes or a template drifts from the package.

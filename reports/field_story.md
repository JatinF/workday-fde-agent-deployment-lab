# Field story

Synthetic engagement SYN-ORG-NORTHLINE. No model is called. No Workday tenant was called.

| Field | Value |
| --- | --- |
| Tokens | 0 |
| Hosted model | not-run |
| Happy-path code | ok |
| Trace | tr-0001 |
| Business-process event | evt-0001 |
| External coverage calls | 1 |
| Retry attempts | 1 |
| Nodes | token_check > gateway_authorize > gateway_authorize > gateway_authorize > gateway_authorize > gateway_authorize > validate_input > read_worker > read_balance > reserve_coverage > submit_business_process |
| Checks passed | 13 |
| Checks failed | 0 |
| Duration ms | 203.4542 |

## Flow

SYN-USER-NOOR submits 8 hours for SYN-USER-IVAN. CoverageInput accepts the payload.
No model is called. The gateway then checks the token, the deploy, Available To,
the tool, and the domain. The action reads the worker and the balance, reserves one
coverage slot, and submits one Request Time Off event. The event row is the audit
record. The trace is the telemetry. A failed dependency does not submit the process.

## Lifecycle FDE-BACKLOG-001

The write skill was loaded without list_time_off_types. Preflight reports prompt_tool_missing. attach_required_prompts restores the catalog WID, and the repaired package submits one Request Time Off event. This was reproduced in the lab from the prompt-tool rule. It was not observed in a customer tenant.

Before: prompt_tool_missing.
After error count: 0.
Repaired invoke: ok.

## Incidents

### authentication_401

401 authentication failure

- Symptom: The coverage request stores no Request Time Off event.
- Telemetry: code=token_invalid class=authentication outcome=failed nodes=token_check,gateway_authorize asor_http=401
- Diagnosis: token_check is rejected and the gateway records token_invalid. A registration POST with no token returns HTTP 401.
- Root cause: The access token is invalid. The lab rejects it before any worker read or coverage call.
- Fix: Authenticate the actor again and use a token issued at the current registration epoch.
- Validation: asor_rejected=401 asor_registered=201 code=ok event_id=evt-0001
- Prevention: token_check stays first, and the bearer secret is removed from the trace.

### authorization_403

403 authorization failure

- Symptom: The worker read is refused and no time-off event is stored.
- Telemetry: code=rest_403 class=permission_failure outcome=failed nodes=token_check,gateway_authorize
- Diagnosis: gateway_authorize on get_worker returns rest_403.
- Root cause: The REST resource call was injected with HTTP 403. Workday documents that status when the resource or the domain policy blocks the caller. This run injects the status. It does not call Workday.
- Fix: Register the resource for the caller and include the caller's groups on the domain policy, then sign in again.
- Validation: code=ok event_id=evt-0001
- Prevention: A 403 stops the action before reserve_coverage and before Request Time Off.

### missing_permission

Missing permission

- Symptom: HR does not see the write skill. The tool is not listed.
- Telemetry: code=not_in_available_to class=permission_failure outcome=not_listed nodes=token_check,gateway_authorize
- Diagnosis: gateway_authorize returns not_in_available_to. request-coverage Available To is managers only.
- Root cause: SYN-USER-HANA is in SYN-SG-HR-PARTNER. That group is not on the write skill.
- Fix: Leave the write skill limited to managers. Send HR to read-balance.
- Validation: read=ok write=not_in_available_to
- Prevention: Preflight rejects SYN-SG-EMPLOYEE on the write skill. The story checks that HR can read and still cannot write.

### invalid_configuration

Invalid configuration

- Symptom: The gateway does not list the tool.
- Telemetry: code=tenant_alias_missing class=configuration_error outcome=failed nodes=token_check,gateway_authorize
- Diagnosis: The first gateway check returns tenant_alias_missing.
- Root cause: The tenant alias is empty. Agent Gateway requires it. A real tenant alias was not issued for this lab.
- Fix: Send the lab org id SYN-ORG-NORTHLINE as the alias on the local stand-in.
- Validation: code=ok event_id=evt-0001
- Prevention: The alias check fails closed before the token is treated as sufficient.

### schema_mismatch

Schema mismatch

- Symptom: The action rejects the body before reading the worker.
- Telemetry: code=schema_mismatch class=malformed_input outcome=failed nodes=token_check,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,validate_input
- Diagnosis: validate_input fails with schema_mismatch because hours arrived as a string.
- Root cause: The request property hours is a number. The payload sent a string. Strict validation does not coerce it.
- Fix: Send hours as an integer.
- Validation: code=ok event_id=evt-0001
- Prevention: CoverageInput is strict. Preflight still requires a description and a sample on every request property.

### malformed_payload

Malformed payload

- Symptom: The action rejects the body and stores no event.
- Telemetry: code=malformed_input class=malformed_input outcome=failed nodes=token_check,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,validate_input
- Diagnosis: validate_input returns malformed_input because client_request_id is absent.
- Root cause: The idempotency field is required. The payload omitted it.
- Fix: Include client_request_id on every write.
- Validation: code=ok event_id=evt-0001
- Prevention: The replay store keys on that field. A write without it is refused.

### timeout

Downstream timeout

- Symptom: The coverage call does not finish inside the synchronous limit.
- Telemetry: code=timed_out class=timeout outcome=timed_out nodes=token_check,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,validate_input,read_worker,read_balance,reserve_coverage
- Diagnosis: reserve_coverage is timed_out. The elapsed virtual clock is past 300000 ms. No business-process event is written.
- Root cause: The injected clock jumps by the timeout plus 1 ms on the first coverage attempt. The calendar host is a fixture.
- Fix: Stay inside the 5-minute synchronous limit. This lab does not run an asynchronous orchestration.
- Validation: code=ok event_id=evt-0001
- Prevention: The timeout is checked before a later retry, and Request Time Off is not submitted after a timeout.

### duplicate_request

Duplicate request

- Symptom: A second submit with the same client_request_id returns the original event.
- Telemetry: code=replayed class=ok outcome=completed nodes=token_check,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,idempotency
- Diagnosis: The idempotency node is replayed. The external call count stays 1 and the event count stays 1.
- Root cause: The key is the actor, the worker, and client_request_id. The client retried that same key.
- Fix: Return the stored event. Do not reserve coverage again and do not submit Request Time Off again.
- Validation: first=ok second=replayed events=1 external_calls=1
- Prevention: The action effect is Idempotent. The lab store enforces it. The store is process memory and does not survive a restart.

### dependency_failure

Dependency failure

- Symptom: The coverage calendar keeps returning an error and no time-off event is stored.
- Telemetry: code=retry_exhausted class=retry_exhausted outcome=failed nodes=token_check,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,gateway_authorize,validate_input,read_worker,read_balance,reserve_coverage,reserve_coverage,reserve_coverage
- Diagnosis: reserve_coverage records the retry nodes and the code is retry_exhausted.
- Root cause: The fixture fails every attempt. The business process waits until coverage succeeds, so a dead dependency creates no time-off event.
- Fix: When the dependency recovers, the same action succeeds on attempt 3 after two failures. Backoff is 10 ms then 20 ms on the virtual clock.
- Validation: code=ok retry_attempts=3 event_id=evt-0001
- Prevention: Attempts are capped at 3. The business process is not submitted after the dependency is exhausted.

### configuration_drift

Configuration drift

- Symptom: A previously usable token is rejected after the agent registration changes.
- Telemetry: code=token_stale class=authentication outcome=failed nodes=token_check,gateway_authorize
- Diagnosis: The token is issued, then gateway_authorize returns token_stale.
- Root cause: The token epoch is 1 and the registration epoch is 2. A token from before the registration change does not match the new epoch.
- Fix: Discard the old token and call again after registration.
- Validation: code=ok event_id=evt-0001
- Prevention: Every tool authorization compares issued_epoch with registration_epoch.

## Contract findings

None.

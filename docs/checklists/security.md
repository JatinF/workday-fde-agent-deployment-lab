# Security checklist

The shipped package passes `fde-lab preflight`. The failing rows are enforced by a mutated package in the suite, not by editing the shipped files.

| Check | Status | Notes |
| --- | --- | --- |
| Custom agent stays Delegate | Met in lab | `ambient-custom-agent` fails preflight. |
| Write Available To is only SYN-SG-MANAGER | Met in lab | Matches the time-off-submit domain. |
| SYN-SG-EMPLOYEE is not on the write skill | Met in lab | `employee-on-write` fails preflight. |
| HR can read and cannot start the write | Met in lab | `hr-read` completes. `hr-write-hidden` is not listed. |
| Manager cannot act outside the chain | Met in lab | `outside-org` and `write-outside-org`. This is a lab chain check, not a Workday supervisory-org report. |
| Domain policy is required in addition to Available To | Met in lab | `rest-403` and `domain` intersection in `security.py`. |
| ASU group is inside the write domain | Met in lab | ASU groups are SYN-SG-MANAGER. Workday did not create the ASU. |
| Prompt tool registered before the write runs | Met in lab | `prompt-wid-missing`. |
| SOAP and REST failures are distinct | Met in lab | `soap-401`, `rest-403`. |
| Business process refuses an unauthorized task | Met in lab | `bp-not-authorized` writes no event. |
| Secrets stay out of traces and gate reasons | Met in lab | Token leak count 0. A blocked tenant gate does not echo the token. |
| No private key in the tree | Met in lab | `scripts/reject_private_keys.py`. The scanner skips itself and does not contain a contiguous key header. |
| Live OAuth client, client secret, and x509 key | Not run | Not created. Do not invent them. |
| Pending security policy activation | Not run | Requires a tenant security administrator. |
| Audit under a real ASU | Not run | No ASU was provisioned. |

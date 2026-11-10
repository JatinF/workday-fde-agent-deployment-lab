# Security model

The custom agent is delegate-only. Ambient mode fails preflight with `ambient_custom_agent`.

Interaction and tool execution are separate. Available To decides who can see a skill. The domain policy decides who can run a tool. Both have to pass. The management-chain check is a lab stand-in for supervisory organization security: only SYN-USER-NOOR can submit time off for SYN-USER-IVAN. SYN-USER-HANA can read balances and cannot start `request-coverage`.

| Group | Read skill | Write skill | Write domain |
| --- | --- | --- | --- |
| SYN-SG-MANAGER | yes | yes | yes |
| SYN-SG-HR-PARTNER | yes | no | no |
| SYN-SG-EMPLOYEE | no | no | no |

The ASU group on the shipped package is SYN-SG-MANAGER. Putting SYN-SG-EMPLOYEE on the write skill fails preflight with `employee_on_write`. Registering a resource does not grant that access.

`security/roles.yaml` and `security/permissions.yaml` are the templates. `security/policies.py` compares them with the package. `fde-lab run-story` fails when they diverge. The YAML is not a Workday security export, and View Security for Agent Skill was not opened.

Tool calls in this process use the lab token after those checks. Workday's custom-agent page says runtime tool calls use the ASU token. The troubleshooting page says each step runs as the signed-in user. This lab fails closed on both the Available To list and the domain policy, and it does not resolve that documentation conflict. No ASU was created in a tenant. The token secret is removed from traces.

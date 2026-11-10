# Production readiness

Decision: NO-GO.

The lab package is internally consistent. A green field story does not move any gate below. The story is a local stand-in. It is not ready for a Workday production tenant, a sandbox, or a customer.

| Gate | Status | Why it blocks production |
| --- | --- | --- |
| Development tenant exercised | Not run | No tenant was requested or signed into. |
| App Builder deploy and App Hub trace | Not run | Artifacts have not been deployed. |
| ASOR registration on the regional host | Not run | The local stand-in is not `us.agent.workday.com`. |
| Security policy activated by an administrator | Not run | View Security for Agent Skill was not run. |
| ASU created by activation | Not run | The YAML group is not an ASU. |
| Request Time Off on a real business process | Not run | The event is an in-memory row. |
| Agent Gateway MCP with a user session | Not run | No MCP session was opened. |
| Sana availability | Not run | Custom agents become available in Sana after activation. That was not observed. |
| Idempotency store that survives a restart | Not met | The replay map is process memory. |
| Coverage vendor | Not met | `coverage.lab.invalid` is not a system anyone operates. |
| Hosted model and token cost | Not run | Tokens 0. No price is applied. |
| Local container run | Not run | Docker is not installed on the workstation. The image build is the Actions `docker-build` job. |
| External users or a design partner | Not met | SYN-ORG-NORTHLINE is synthetic. |

A later change can move a single gate to passed only after the command, the tenant alias, and the result are recorded without secrets. Do not mark a gate passed from this document or from `reports/field_story.md`.

# Customer discovery

This document is the discovery record for a synthetic engagement. No customer was interviewed. No Workday tenant was opened.

## Account

| Field | Value |
| --- | --- |
| Org | SYN-ORG-NORTHLINE |
| Engagement | SYN-ENGAGE-TIMEOFF-001 |
| Manager | SYN-USER-NOOR |
| Worker in chain | SYN-USER-IVAN, 16 hours remaining |
| HR partner | SYN-USER-HANA |
| Worker outside the chain | SYN-USER-OTTO |
| Process | Request Time Off |
| External system | Lab coverage calendar at `https://coverage.lab.invalid/slots` |

## Job to be done

A manager asks how much time off a worker has, then books a block of hours and leaves a coverage note. HR can read any balance in the fixture. HR cannot submit the business process. An employee cannot start the write skill. A manager cannot book time off for a worker they do not manage.

## Decisions forced by that job

- The agent is a custom agent, so it stays in delegate mode. Ambient mode is a configuration error.
- Two skills, not one skill that both reads and writes. The read skill's Available To list is wider than the write skill's list.
- The write path needs a prompt tool for the time-off type. A write registered without that prompt tool is rejected before the business process starts.
- The external coverage call can fail with 503. The action retries it. The business-process submit is not retried blindly. A repeated `client_request_id` returns the original event.
- The coverage system is a fixture. There is no vendor contract and no live credential.

## Out of scope

Production promotion, Sana, a hosted model, a real supervisory organization, and any worker data outside the four fixture rows.

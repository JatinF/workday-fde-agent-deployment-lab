# ADR 0004: Idempotency key

Status: accepted. Date: 2026-11-09.

The replay key is the actor, the worker, and `client_request_id`. A second call returns the original Request Time Off event and does not call the coverage fixture again. The Orchestrate effect annotation on the action is Idempotent. The store is what enforces the annotation.

The store is process memory. A restart loses it. That is why production readiness says the surviving store is not met.

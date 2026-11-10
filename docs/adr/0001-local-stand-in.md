# ADR 0001: Local stand-in

Status: accepted. Date: 2026-11-09.

The lab checks Workday artifact shapes and failure order in process. It does not call a development tenant, App Builder, ASOR, Agent Gateway, Sana, or Orchestration Builder. Those gates stay not-run until a command, a tenant alias, and a result are recorded without secrets.

The runtime is a deterministic skill router. It does not call a model. Tokens are 0. No price is applied.

from __future__ import annotations

from fde_lab.load import load_package
from fde_lab.models import FailureClass, Faults, InvokeRequest
from fde_lab.runtime import Runtime
from fde_lab.tokens import redact_text


def _write(request_id: str, faults: Faults | None = None) -> InvokeRequest:
    return InvokeRequest(
        actor_id="SYN-USER-NOOR",
        skill="request-coverage",
        arguments={
            "worker_id": "SYN-USER-IVAN",
            "hours": 8,
            "time_off_type_wid": "fde00000000000000000000000000031",
            "client_request_id": request_id,
        },
        faults=faults or Faults(),
    )


def test_replay_does_not_submit_twice() -> None:
    runtime = Runtime(load_package())
    first = runtime.invoke(_write("req-1"))
    second = runtime.invoke(_write("req-1"))
    assert first.failure_class == FailureClass.OK
    assert second.code == "replayed"
    assert first.business_process_event_id == second.business_process_event_id
    assert len(runtime.state.events) == 1
    assert runtime.state.external_calls == 1


def test_direct_api_is_refused() -> None:
    trace = Runtime(load_package()).invoke(_write("req-direct", Faults(direct_api=True)))
    assert trace.code == "direct_api_blocked"
    assert trace.runbook_section == "agent-gateway-mcp"


def test_redact_removes_lab_tokens() -> None:
    assert "lab-token-" not in redact_text("upstream said Bearer lab-token-SYN-USER-NOOR-1-1")

"""Local HTTP surface for preflight, invoke, traces, and the ASOR stand-in."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fde_lab import __version__
from fde_lab.asor import AsorService
from fde_lab.gates import all_gates
from fde_lab.log import RequestLogMiddleware
from fde_lab.models import InvokeRequest
from fde_lab.preflight import preflight
from fde_lab.runtime import Runtime
from fde_lab.story import run_story

_asor = AsorService()


def create_app(runtime: Runtime | None = None) -> FastAPI:
    app = FastAPI(title="Workday FDE agent deployment lab", version=__version__)
    app.add_middleware(RequestLogMiddleware)
    app.state.runtime = runtime or Runtime.load()

    @app.get("/health")
    def health() -> dict[str, object]:
        gates = {gate.name: gate.status for gate in all_gates()}
        return {
            "status": "ok",
            "version": __version__,
            "hosted_llm": "not-run",
            "tokens": 0,
            "gates": gates,
        }

    @app.get("/gates")
    def gates() -> dict[str, object]:
        return {"gates": [gate.model_dump() for gate in all_gates()]}

    @app.post("/preflight")
    def run_preflight() -> dict[str, object]:
        findings = preflight(app.state.runtime.package)
        errors = [item for item in findings if item.severity == "error"]
        return {
            "ok": not errors,
            "findings": [item.model_dump() for item in findings],
        }

    @app.post("/invoke")
    def invoke(body: InvokeRequest) -> dict[str, object]:
        return _dump(app.state.runtime.invoke(body))

    @app.get("/story")
    def field_story() -> dict[str, object]:
        return _dump(run_story())

    @app.get("/traces/{trace_id}")
    def read_trace(trace_id: str) -> dict[str, object]:
        trace = app.state.runtime.traces.get(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="trace not found")
        return _dump(trace)

    @app.post("/asor/agentDefinition")
    async def post_agent(request: Request) -> JSONResponse:
        body = await request.json()
        token = app.state.runtime.tokens.authenticate(request.headers.get("authorization"))
        domains = _domains(request)
        if _alias_missing(request):
            return JSONResponse(status_code=400, content={"error": "tenant alias is required"})
        result = _asor.post(body, token, domains, app.state.runtime.state)
        return JSONResponse(status_code=result.status, content=result.body)

    @app.get("/asor/agentDefinition/{agent_id}")
    def get_agent(agent_id: str, request: Request) -> JSONResponse:
        token = app.state.runtime.tokens.authenticate(request.headers.get("authorization"))
        if _alias_missing(request):
            return JSONResponse(status_code=400, content={"error": "tenant alias is required"})
        result = _asor.get(agent_id, token, _domains(request), app.state.runtime.state)
        return JSONResponse(status_code=result.status, content=result.body)

    return app


def _dump(model: BaseModel) -> dict[str, object]:
    raw = model.model_dump()
    dumped: dict[str, object] = {}
    for key, value in raw.items():
        dumped[str(key)] = value
    return dumped


def _domains(request: Request) -> set[str]:
    raw = request.headers.get("x-lab-domains", "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _alias_missing(request: Request) -> bool:
    return not request.headers.get("wd-agent-tenant-alias", "").strip()

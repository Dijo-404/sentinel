"""FastAPI routes for case-api.v1."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from sentinel_api import CONTRACT_VERSION, __version__
from sentinel_api.adapters.http.auth import CompositePrincipalResolver, TokenMap
from sentinel_api.application.service import CaseService
from sentinel_api.domain.types import DomainError


def create_app(
    *,
    service: CaseService,
    tokens: TokenMap | CompositePrincipalResolver,
    mode: str,
    readiness: Any,
) -> FastAPI:
    app = FastAPI(title="sentinel-api", version=__version__)
    app.state.service = service
    app.state.tokens = tokens
    app.state.mode = mode
    app.state.readiness = readiness

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        request_id = request.headers.get("x-request-id", "request-local")
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "request_id": request_id},
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        report = readiness()
        status = 200 if report.get("ready") else 503
        return JSONResponse(status_code=status, content=report)

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": "case-api",
            "mode": mode,
        }

    def auth(request: Request):
        return tokens.resolve(request.headers.get("authorization"))

    @app.post("/v1/cases")
    def create_case(request: Request, body: dict[str, Any]) -> JSONResponse:
        principal = auth(request)
        key = request.headers.get("idempotency-key") or ""
        created, status = service.create_case(principal, body, idempotency_key=key)
        return JSONResponse(status_code=status, content=created.to_dict())

    @app.get("/v1/cases/{case_id}")
    def get_case(case_id: str, request: Request) -> dict[str, Any]:
        return service.get_case(auth(request), case_id).to_dict()

    @app.post("/v1/cases/{case_id}/messages")
    def post_message(case_id: str, request: Request, body: dict[str, Any]) -> JSONResponse:
        case = service.add_message(auth(request), case_id, body)
        return JSONResponse(status_code=202, content=case.to_dict())

    @app.get("/v1/cases/{case_id}/events")
    def get_events(case_id: str, request: Request) -> Response:
        principal = auth(request)
        after_raw = request.query_params.get("after")
        last_event = request.headers.get("last-event-id")
        cursor = 0
        if after_raw is not None:
            try:
                cursor = int(after_raw)
            except ValueError as exc:
                raise DomainError("INVALID_INPUT", "after must be an int", 422) from exc
        elif last_event is not None:
            try:
                cursor = int(last_event)
            except ValueError as exc:
                raise DomainError("INVALID_INPUT", "Last-Event-ID must be an int", 422) from exc
        events = service.list_events(principal, case_id, after=cursor)
        if request.query_params.get("format") == "json":
            return JSONResponse({"events": [e.to_dict() for e in events]})

        def stream():
            for event in events:
                data = json.dumps(event.to_dict(), separators=(",", ":"), ensure_ascii=False)
                yield f"id: {event.sequence}\ndata: {data}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/v1/customer/dashboard")
    def customer_dashboard(request: Request) -> dict[str, Any]:
        return service.customer_dashboard(auth(request))

    @app.get("/v1/customer/cases")
    def customer_cases(request: Request) -> dict[str, Any]:
        return service.customer_cases(auth(request))

    @app.get("/v1/operator/dashboard")
    def operator_dashboard(request: Request) -> dict[str, Any]:
        return service.operator_dashboard(auth(request))

    @app.get("/v1/supervisor/dashboard")
    def supervisor_dashboard(request: Request) -> dict[str, Any]:
        return service.supervisor_dashboard(auth(request))

    @app.get("/v1/ops/cases")
    def ops_queue(request: Request) -> dict[str, Any]:
        status = request.query_params.get("status")
        after = request.query_params.get("after")
        cases, next_cursor = service.list_queue(auth(request), status=status, after=after)
        body: dict[str, Any] = {"cases": [c.to_dict() for c in cases]}
        if next_cursor is not None:
            body["next_cursor"] = next_cursor
        return body

    @app.get("/v1/ops/messages")
    def ops_messages(request: Request) -> dict[str, Any]:
        after = request.query_params.get("after")
        messages, next_cursor = service.list_ops_messages(auth(request), after=after)
        body: dict[str, Any] = {"messages": messages}
        if next_cursor is not None:
            body["next_cursor"] = next_cursor
        return body

    @app.get("/v1/ops/audit-events")
    def ops_audit_events(request: Request) -> dict[str, Any]:
        after = request.query_params.get("after")
        events, next_cursor = service.list_ops_audit_events(auth(request), after=after)
        body: dict[str, Any] = {"events": events}
        if next_cursor is not None:
            body["next_cursor"] = next_cursor
        return body

    @app.get("/v1/ops/cases/{case_id}/evidence")
    def ops_evidence(case_id: str, request: Request) -> dict[str, Any]:
        authorization = request.headers.get("authorization") or ""
        bundle = service.get_ops_evidence(auth(request), case_id, authorization=authorization)
        return bundle.to_dict()

    @app.post("/v1/ops/cases/{case_id}/claim")
    def ops_claim(case_id: str, request: Request) -> dict[str, Any]:
        return service.claim_case(auth(request), case_id).to_dict()

    @app.post("/v1/ops/actions/{action_id}/decisions")
    def ops_decide(action_id: str, request: Request, body: dict[str, Any]) -> dict[str, Any]:
        authorization = request.headers.get("authorization") or ""
        approval = service.decide(auth(request), action_id, body, authorization=authorization)
        return approval.to_dict()

    @app.post("/v1/ops/cases/{case_id}/escalate")
    def ops_escalate(case_id: str, request: Request, body: dict[str, Any]) -> dict[str, Any]:
        return service.escalate(auth(request), case_id, body).to_dict()

    @app.get("/v1/internal/cases/{case_id}/input")
    def internal_input(case_id: str, request: Request) -> dict[str, Any]:
        revision_raw = request.query_params.get("revision")
        if revision_raw is None:
            raise DomainError("INVALID_INPUT", "revision query is required", 422)
        try:
            revision = int(revision_raw)
        except ValueError as exc:
            raise DomainError("INVALID_INPUT", "revision must be an int", 422) from exc
        return service.get_input(auth(request), case_id, revision).to_dict()

    @app.post("/v1/internal/cases/{case_id}/results")
    def internal_results(case_id: str, request: Request, body: dict[str, Any]) -> dict[str, Any]:
        return service.apply_result(auth(request), case_id, body).to_dict()

    return app

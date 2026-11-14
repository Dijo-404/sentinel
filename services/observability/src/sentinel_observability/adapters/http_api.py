"""FastAPI boundary for observability.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import ObservabilityError
from ..application.service import ObservabilityService
from ..domain.types import CONTRACT_VERSION, PORT
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    service: ObservabilityService
    mode: str
    component: str = "observability"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-observability", version="0.1.0")
    app.state.services = services

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict:
        return {"status": "ready", "mode": services.mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": services.component,
            "mode": services.mode,
            "port": PORT,
            "financial_audit": False,
            "financial_authority": False,
        }

    @app.get("/v1/signals")
    def list_signals(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            items = services.service.list_signals(principal)
            return JSONResponse(
                {
                    "signals": [item.to_wire() for item in items],
                    "financial_audit": False,
                }
            )
        except ObservabilityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/spans")
    def list_spans(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            items = services.service.list_spans(principal)
            return JSONResponse(
                {
                    "spans": [item.to_span_wire() for item in items],
                    "financial_audit": False,
                }
            )
        except ObservabilityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/ingest")
    async def ingest(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            accepted = services.service.ingest(principal, body)
            return JSONResponse({"accepted": accepted, "financial_audit": False})
        except ObservabilityError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: ObservabilityError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

"""FastAPI boundary for platform-ai.v1 routes (metadata only)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import PlatformAiError
from ..application.service import PlatformAiService
from ..domain.types import CONTRACT_VERSION
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    service: PlatformAiService
    mode: str
    component: str = "platform-ai"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-platform-ai", version="0.1.0")
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
            "money_authority": False,
        }

    @app.get("/v1/config")
    def get_config(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            config = services.service.get_config(principal)
            return JSONResponse(config.to_wire())
        except PlatformAiError as exc:
            return _error(exc, request_id)

    @app.get("/v1/runs")
    def list_runs(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            runs = services.service.list_runs(principal)
            return JSONResponse({"runs": [run.to_wire() for run in runs]})
        except PlatformAiError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: PlatformAiError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

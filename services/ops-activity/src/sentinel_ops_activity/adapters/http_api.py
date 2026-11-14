"""FastAPI boundary for ops-activity.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.activity import ActivityService
from ..application.errors import OpsActivityError
from ..domain.types import CONTRACT_VERSION
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    activity: ActivityService
    mode: str
    component: str = "ops-activity"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-ops-activity", version="0.1.0")
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
            "port": "ops-activity.v1",
            "financial_authority": False,
        }

    @app.get("/v1/activity")
    def list_activity(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            items = services.activity.list_activity(principal)
            return JSONResponse({"items": [item.to_wire() for item in items]})
        except OpsActivityError as exc:
            return _error(exc, request_id)

    return app


def _error(exc: OpsActivityError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

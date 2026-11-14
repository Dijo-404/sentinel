"""FastAPI boundary for evaluation.v1 RunReport query routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_evaluation.adapters.auth import TokenAuthenticator
from sentinel_evaluation.application.errors import EvaluationError
from sentinel_evaluation.application.reports import ReportQueryService
from sentinel_evaluation.domain.models import CONTRACT_VERSION


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    service: ReportQueryService
    mode: str
    component: str = "evaluation"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-evaluation", version="0.1.0")
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

    @app.get("/v1/reports")
    def list_reports(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            reports = services.service.list_reports(principal)
            return JSONResponse({"reports": list(reports)})
        except EvaluationError as exc:
            return _error(exc, request_id)

    @app.get("/v1/reports/{run_id}")
    def get_report(run_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            report = services.service.get_report(principal, run_id)
            return JSONResponse(report)
        except EvaluationError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: EvaluationError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

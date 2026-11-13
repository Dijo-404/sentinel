"""FastAPI boundary for merchant-analytics.v1 routes (read-only)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import AnalyticsError, ValidationError
from ..application.get_metrics import GetMerchantMetrics
from ..domain.types import CONTRACT_VERSION
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    get_metrics: GetMerchantMetrics
    mode: str
    component: str = "merchant-analytics"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-analytics", version="0.1.0")
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
        }

    @app.get("/v1/merchants/{merchant_ref}/metrics")
    def merchant_metrics(merchant_ref: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            window_start = request.query_params.get("window_start")
            window_end = request.query_params.get("window_end")
            if not window_start or not window_end:
                raise ValidationError("window_start and window_end are required")
            result = services.get_metrics(
                principal,
                merchant_ref=merchant_ref,
                window_start=window_start,
                window_end=window_end,
            )
            return JSONResponse(result.to_wire())
        except AnalyticsError as exc:
            return _error(exc, request_id)

    @app.api_route(
        "/v1/merchants/{merchant_ref}/metrics",
        methods=["POST", "PUT", "PATCH", "DELETE"],
    )
    def merchant_metrics_mutations(merchant_ref: str, request: Request) -> JSONResponse:
        del merchant_ref
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        return JSONResponse(
            {
                "code": "METHOD_NOT_ALLOWED",
                "message": "merchant-analytics.v1 metrics are read-only",
                "request_id": request_id,
            },
            status_code=405,
            headers={"Allow": "GET, HEAD, OPTIONS"},
        )

    return app


def _error(exc: AnalyticsError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

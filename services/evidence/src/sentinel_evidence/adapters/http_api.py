"""FastAPI boundary for evidence.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.collect import CollectEvidence, ListEvidence
from ..application.errors import EvidenceError, ValidationError
from ..domain.types import CONTRACT_VERSION, CollectRequest
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    collect: CollectEvidence
    list_evidence: ListEvidence
    mode: str
    component: str = "evidence"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-evidence", version="0.1.0")
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

    @app.post("/v1/evidence/collect")
    async def collect(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            if set(body) - {"case_id", "case_revision", "order_reference"}:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("case_id", "case_revision", "order_reference"):
                if key not in body:
                    raise ValidationError(f"{key} is required")
            result = services.collect(
                principal,
                CollectRequest(
                    case_id=body["case_id"],
                    case_revision=body["case_revision"],
                    order_reference=body["order_reference"],
                ),
            )
            return JSONResponse(result.to_wire())
        except EvidenceError as exc:
            return _error(exc, request_id)

    @app.get("/v1/cases/{case_id}/evidence")
    def list_case_evidence(case_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.list_evidence(principal, case_id)
            return JSONResponse(result.to_wire())
        except EvidenceError as exc:
            return _error(exc, request_id)

    return app


def _error(exc: EvidenceError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

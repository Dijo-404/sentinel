"""FastAPI boundary for merchant-disputes.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.disputes import DisputeService
from ..application.errors import DisputeError, ValidationError
from ..domain.types import CONTRACT_VERSION, CreateDisputeRequest
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    disputes: DisputeService
    mode: str
    component: str = "merchant-disputes"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-disputes", version="0.1.0")
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

    @app.post("/v1/disputes")
    async def create_dispute(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            allowed = {"case_id", "merchant_ref", "reason_code", "deadline_at", "order_reference"}
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("case_id", "merchant_ref", "reason_code"):
                if key not in body or not str(body[key]).strip():
                    raise ValidationError(f"{key} is required")
            result = services.disputes.create(
                principal,
                CreateDisputeRequest(
                    case_id=str(body["case_id"]),
                    merchant_ref=str(body["merchant_ref"]),
                    reason_code=str(body["reason_code"]),
                    deadline_at=str(body["deadline_at"]) if "deadline_at" in body else None,
                    order_reference=(
                        str(body["order_reference"]) if "order_reference" in body else None
                    ),
                ),
                idempotency_key=request.headers.get("idempotency-key"),
            )
            return JSONResponse(result.to_wire(), status_code=201)
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.get("/v1/disputes/{dispute_id}")
    def get_dispute(dispute_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.disputes.get(principal, dispute_id)
            return JSONResponse(result.to_wire())
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.get("/v1/merchants/{merchant_ref}/disputes")
    def list_merchant_disputes(merchant_ref: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            items = services.disputes.list(principal, merchant_ref)
            return JSONResponse({"disputes": [item.to_wire() for item in items]})
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.post("/v1/disputes/{dispute_id}/packets")
    def collect_packet(dispute_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.disputes.collect_packet(principal, dispute_id)
            return JSONResponse(result.to_wire())
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.post("/v1/disputes/{dispute_id}/submit")
    def submit_dispute(dispute_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.disputes.submit(principal, dispute_id)
            return JSONResponse(result.to_wire())
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.post("/v1/disputes/{dispute_id}/resolve")
    async def resolve_dispute(dispute_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            if set(body) - {"outcome"}:
                raise ValidationError("Undeclared fields are not permitted")
            if "outcome" not in body:
                raise ValidationError("outcome is required")
            outcome = str(body["outcome"])
            if outcome not in {"WON", "LOST", "WITHDRAWN"}:
                raise ValidationError("outcome must be WON, LOST, or WITHDRAWN")
            result = services.disputes.resolve(principal, dispute_id, outcome)  # type: ignore[arg-type]
            return JSONResponse(result.to_wire())
        except DisputeError as exc:
            return _error(exc, request_id)

    @app.get("/v1/disputes/{dispute_id}/deadline")
    def dispute_deadline(dispute_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.disputes.deadline(principal, dispute_id)
            return JSONResponse(result.to_wire())
        except DisputeError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: DisputeError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

"""FastAPI adapter for merchant-settlement.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_merchant_settlement.adapters.auth import TokenMap
from sentinel_merchant_settlement.application.errors import SettlementError, ValidationError
from sentinel_merchant_settlement.application.findings import ManageFindings
from sentinel_merchant_settlement.application.import_batch import (
    ImportSettlementBatch,
    build_batch_from_csv,
    build_batch_from_dict,
)
from sentinel_merchant_settlement.domain.types import COMPONENT, CONTRACT_VERSION, batch_as_dict


@dataclass
class AppServices:
    tokens: TokenMap
    import_batch: ImportSettlementBatch
    findings: ManageFindings
    mode: str


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-settlement", version="0.1.0")
    app.state.services = services

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready", "mode": services.mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": services.mode,
            "port": "merchant-settlement.v1",
        }

    @app.post("/v1/settlements/batches")
    async def import_batch(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.tokens.resolve(request.headers.get("authorization"))
            body: Any = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("Body must be a JSON object")
            if "csv_text" in body:
                required = {
                    "batch_id",
                    "tenant_id",
                    "merchant_ref",
                    "period_start",
                    "period_end",
                    "currency",
                    "csv_text",
                }
                if set(body) - required:
                    raise ValidationError("Undeclared fields are not permitted")
                missing = required - set(body)
                if missing:
                    raise ValidationError(f"Missing fields: {', '.join(sorted(missing))}")
                batch = build_batch_from_csv(
                    batch_id=str(body["batch_id"]),
                    tenant_id=str(body["tenant_id"]),
                    merchant_ref=str(body["merchant_ref"]),
                    period_start=str(body["period_start"]),
                    period_end=str(body["period_end"]),
                    currency=str(body["currency"]),
                    csv_text=str(body["csv_text"]),
                )
            else:
                batch = build_batch_from_dict(body)
            result = services.import_batch(principal, batch)
            return JSONResponse(status_code=201, content=result.as_dict())
        except SettlementError as exc:
            return _error(exc, request_id)

    @app.get("/v1/settlements/batches/{batch_id}")
    def get_batch(batch_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.tokens.resolve(request.headers.get("authorization"))
            batch = services.findings.get_batch(principal, batch_id)
            return JSONResponse(batch_as_dict(batch))
        except SettlementError as exc:
            return _error(exc, request_id)

    @app.get("/v1/settlements/findings")
    def list_findings(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.tokens.resolve(request.headers.get("authorization"))
            batch_id = request.query_params.get("batch_id")
            status = request.query_params.get("status")
            items = services.findings.list(principal, batch_id=batch_id, status=status)
            return JSONResponse({"findings": [f.as_dict() for f in items]})
        except SettlementError as exc:
            return _error(exc, request_id)

    @app.post("/v1/settlements/findings/{finding_id}/assign")
    async def assign_finding(finding_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.tokens.resolve(request.headers.get("authorization"))
            body: Any = await request.json()
            if not isinstance(body, dict) or set(body) != {"assignee"}:
                raise ValidationError("Body must be {assignee}")
            finding = services.findings.assign(principal, finding_id, str(body["assignee"]))
            return JSONResponse(finding.as_dict())
        except SettlementError as exc:
            return _error(exc, request_id)

    @app.post("/v1/settlements/findings/{finding_id}/close")
    async def close_finding(finding_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.tokens.resolve(request.headers.get("authorization"))
            if request.headers.get("content-length") not in {None, "0"}:
                body = await request.body()
                if body.strip() not in {b"", b"{}"}:
                    raise ValidationError("close accepts empty body only")
            finding = services.findings.close(principal, finding_id)
            return JSONResponse(finding.as_dict())
        except SettlementError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: SettlementError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

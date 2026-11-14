"""FastAPI boundary for risk.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import RiskError, ValidationError
from ..application.risk import RiskService
from ..domain.types import (
    CONTRACT_VERSION,
    CreateInvestigationRequest,
    RecordFindingRequest,
    RestrictionDecisionRequest,
)
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    risk: RiskService
    mode: str
    component: str = "risk"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-risk", version="0.1.0")
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
            "port": "risk.v1",
            "financial_authority": False,
        }

    @app.get("/v1/risk/dashboard")
    def dashboard(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.risk.dashboard(principal)
            return JSONResponse(result.to_wire())
        except RiskError as exc:
            return _error(exc, request_id)

    @app.get("/v1/risk/investigations")
    def list_investigations(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            case_id = request.query_params.get("case_id")
            items = services.risk.list_investigations(principal, case_id=case_id)
            return JSONResponse({"investigations": [item.to_wire() for item in items]})
        except RiskError as exc:
            return _error(exc, request_id)

    @app.post("/v1/risk/investigations")
    async def create_investigation(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            allowed = {
                "case_id",
                "reason_code",
                "queue_ref",
                "severity",
                "case_revision",
                "evidence_ids",
                "review_due_at",
            }
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("case_id", "reason_code"):
                if key not in body or not str(body[key]).strip():
                    raise ValidationError(f"{key} is required")
            evidence_ids = body.get("evidence_ids") or []
            if not isinstance(evidence_ids, list):
                raise ValidationError("evidence_ids must be an array")
            result = services.risk.create_investigation(
                principal,
                CreateInvestigationRequest(
                    case_id=str(body["case_id"]),
                    reason_code=str(body["reason_code"]),
                    queue_ref=str(body.get("queue_ref", "FRAUD")),
                    severity=str(body.get("severity", "MEDIUM")),
                    case_revision=(int(body["case_revision"]) if "case_revision" in body else None),
                    evidence_ids=tuple(str(x) for x in evidence_ids),
                    review_due_at=(str(body["review_due_at"]) if "review_due_at" in body else None),
                ),
                idempotency_key=request.headers.get("idempotency-key"),
            )
            return JSONResponse(result.to_wire(), status_code=201)
        except RiskError as exc:
            return _error(exc, request_id)

    @app.get("/v1/risk/investigations/{investigation_id}")
    def get_investigation(investigation_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            result = services.risk.get_investigation(principal, investigation_id)
            return JSONResponse(result.to_wire())
        except RiskError as exc:
            return _error(exc, request_id)

    @app.post("/v1/risk/investigations/{investigation_id}/findings")
    async def record_finding(investigation_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            allowed = {"classification", "evidence_ids", "notes", "expected_revision"}
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            if "classification" not in body:
                raise ValidationError("classification is required")
            evidence_ids = body.get("evidence_ids") or []
            if not isinstance(evidence_ids, list):
                raise ValidationError("evidence_ids must be an array")
            result = services.risk.record_finding(
                principal,
                investigation_id,
                RecordFindingRequest(
                    classification=str(body["classification"]),  # type: ignore[arg-type]
                    evidence_ids=tuple(str(x) for x in evidence_ids),
                    notes=str(body.get("notes", "")),
                    expected_revision=(
                        int(body["expected_revision"]) if "expected_revision" in body else None
                    ),
                ),
            )
            return JSONResponse(result.to_wire(), status_code=201)
        except RiskError as exc:
            return _error(exc, request_id)

    @app.post("/v1/risk/restrictions/{restriction_id}/decision")
    async def restriction_decision(restriction_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("JSON object required")
            allowed = {"decision", "reason", "evidence_ids", "expected_revision"}
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("decision", "reason"):
                if key not in body or not str(body[key]).strip():
                    raise ValidationError(f"{key} is required")
            evidence_ids = body.get("evidence_ids") or []
            if not isinstance(evidence_ids, list):
                raise ValidationError("evidence_ids must be an array")
            result = services.risk.decide_restriction(
                principal,
                restriction_id,
                RestrictionDecisionRequest(
                    decision=str(body["decision"]),  # type: ignore[arg-type]
                    reason=str(body["reason"]),
                    evidence_ids=tuple(str(x) for x in evidence_ids),
                    expected_revision=(
                        int(body["expected_revision"]) if "expected_revision" in body else None
                    ),
                ),
            )
            return JSONResponse(result.to_wire())
        except RiskError as exc:
            return _error(exc, request_id)

    @app.get("/v1/risk/cases/{case_id}/blocks")
    def case_blocks(case_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            blocked = services.risk.case_blocks_financial_actions(principal, case_id)
            return JSONResponse(
                {
                    "case_id": case_id,
                    "blocks_financial_actions": blocked,
                    "financial_approval_granted": False,
                }
            )
        except RiskError as exc:
            return _error(exc, request_id)

    # AUTH-21: any ledger approval attempt through this service is denied.
    @app.post("/v1/ops/actions/{action_id}/decisions")
    def deny_ledger_decision(action_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            services.risk.deny_ledger_approval(principal, action_id=action_id)
            return JSONResponse({"ok": False}, status_code=500)
        except RiskError as exc:
            return _error(exc, request_id)

    @app.post("/v1/ledger/approvals")
    def deny_ledger_approvals(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            services.risk.deny_ledger_approval(principal, action_id="ledger-proxy")
            return JSONResponse({"ok": False}, status_code=500)
        except RiskError as exc:
            return _error(exc, request_id)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: RiskError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

"""FastAPI surface for merchant-refunds.v1."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from sentinel_merchant_refunds import (
    COMPONENT,
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    __version__,
)
from sentinel_merchant_refunds.adapters.auth import TokenPrincipalMap
from sentinel_merchant_refunds.application.service import MerchantRefundService
from sentinel_merchant_refunds.domain.errors import MerchantRefundsError, ValidationError
from sentinel_merchant_refunds.domain.status import is_customer_credit
from sentinel_merchant_refunds.domain.types import ApprovalDecision, DraftCreate, DraftUpdate


def create_app(
    *,
    service: MerchantRefundService,
    auth: TokenPrincipalMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-refunds", version=__version__)
    app.state.service = service
    app.state.auth = auth
    app.state.mode = mode

    @app.exception_handler(MerchantRefundsError)
    async def handle_error(request: Request, exc: MerchantRefundsError) -> JSONResponse:
        request_id = request.headers.get("x-request-id", "request-local")
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "request_id": request_id},
        )

    def principal(authorization: str | None):
        return auth.resolve(authorization)

    def enrich(request_obj) -> dict[str, Any]:
        body = request_obj.as_wire()
        body["credit_verified"] = is_customer_credit(request_obj.ledger_status, request_obj.status)
        body["ledger_status"] = request_obj.ledger_status
        # Operational fields needed to bind approvals; not financial authority.
        body["action_digest"] = request_obj.action_digest
        body["case_revision"] = request_obj.case_revision
        body["policy_version"] = request_obj.policy_version
        return body

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        label = "fixture-ready" if mode == "fixture" else "real-peers-ready"
        return {"status": label, "mode": mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": mode,
            "port": PORT,
            "contract_sha256": CONTRACT_SHA256,
        }

    @app.post("/v1/refund-requests", status_code=201)
    def create_refund_request(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency-Key required")
        draft = DraftCreate.model_validate(body)
        created = service.create_draft(
            principal(authorization), draft, idempotency_key=idempotency_key
        )
        return JSONResponse(status_code=201, content=enrich(created))

    @app.get("/v1/refund-requests/{request_id}")
    def get_refund_request(
        request_id: str,
        authorization: str | None = Header(default=None),
    ):
        found = service.get(principal(authorization), request_id)
        return enrich(found)

    @app.patch("/v1/refund-requests/{request_id}")
    def patch_refund_request(
        request_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        updated = service.update_draft(
            principal(authorization), request_id, DraftUpdate.model_validate(body)
        )
        return enrich(updated)

    @app.post("/v1/refund-requests/{request_id}/submit")
    def submit_refund_request(
        request_id: str,
        authorization: str | None = Header(default=None),
    ):
        submitted = service.submit(principal(authorization), request_id)
        return enrich(submitted)

    @app.post("/v1/refund-requests/{request_id}/decisions")
    def decide_refund_request(
        request_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        decided = service.apply_decision(
            principal(authorization),
            request_id,
            ApprovalDecision.model_validate(body),
        )
        return enrich(decided)

    @app.post("/v1/refund-requests/{request_id}/sync")
    def sync_refund_request(
        request_id: str,
        authorization: str | None = Header(default=None),
    ):
        synced = service.sync(principal(authorization), request_id)
        return enrich(synced)

    return app

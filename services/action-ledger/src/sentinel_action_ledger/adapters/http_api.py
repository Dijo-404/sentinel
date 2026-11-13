"""FastAPI surface for action-ledger.v1."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from sentinel_action_ledger import COMPONENT, CONTRACT_VERSION, __version__
from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap
from sentinel_action_ledger.application.service import ActionLedgerService
from sentinel_action_ledger.domain.errors import LedgerError
from sentinel_action_ledger.domain.types import ActionRecord, Approval, ClaimResult


def _record_json(record: ActionRecord) -> dict[str, Any]:
    body: dict[str, Any] = {
        "action_id": record.action_id,
        "provider_ref": record.provider_ref,
        "payload": record.payload,
        "action_digest": record.action_digest,
        "status": record.status,
    }
    if record.approval is not None:
        body["approval"] = asdict(record.approval)
    return body


def _approval_json(approval: Approval) -> dict[str, Any]:
    return asdict(approval)


def _claim_json(result: ClaimResult) -> dict[str, Any]:
    return {
        "commands": [
            {
                "action_id": c.action_id,
                "provider_ref": c.provider_ref,
                "payload": c.payload,
                "action_digest": c.action_digest,
                "lease_id": c.lease_id,
                "lease_expires_at": c.lease_expires_at,
                "provider_capabilities": c.provider_capabilities,
            }
            for c in result.commands
        ]
    }


def create_app(
    *,
    service: ActionLedgerService,
    auth: TokenPrincipalMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-action-ledger", version=__version__)
    app.state.service = service
    app.state.auth = auth
    app.state.mode = mode

    @app.exception_handler(LedgerError)
    async def ledger_error(_request: Request, exc: LedgerError) -> JSONResponse:
        request_id = _request.headers.get("x-request-id", "request-local")
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "request_id": request_id},
        )

    def principal(authorization: str | None):
        return auth.resolve(authorization)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        label = "fixture-ready" if mode == "fixture" else "real-peers-ready"
        return {"status": label}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": mode,
        }

    @app.post("/v1/actions/proposals", status_code=201)
    def propose(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        record, created = service.propose(
            principal(authorization),
            operation_key=body["operation_key"],
            payload=body["payload"],
            digest=body["action_digest"],
        )
        return JSONResponse(status_code=201 if created else 200, content=_record_json(record))

    @app.post("/v1/actions/{action_id}/decisions")
    def decide(
        action_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        approval = service.decide(
            principal(authorization),
            action_id=action_id,
            decision=body["decision"],
            action_digest_value=body["action_digest"],
            case_revision=body["case_revision"],
            policy_version=body["policy_version"],
            expires_at=body["expires_at"],
        )
        return _approval_json(approval)

    @app.post("/v1/actions/reservations")
    def reserve(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        record, created = service.reserve(
            principal(authorization),
            operation_key=body["operation_key"],
            payload=body["payload"],
            digest=body["action_digest"],
            approval_id=body["approval_id"],
            order_reference=body.get("order_reference"),
        )
        return JSONResponse(status_code=201 if created else 200, content=_record_json(record))

    @app.post("/v1/actions/claims")
    def claims(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        result = service.claim(principal(authorization), limit=body["limit"])
        return _claim_json(result)

    @app.get("/v1/actions/{action_id}")
    def get_action(
        action_id: str,
        authorization: str | None = Header(default=None),
    ):
        return _record_json(service.get(principal(authorization), action_id=action_id))

    @app.post("/v1/actions/{action_id}/outcomes")
    def outcomes(
        action_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        record = service.outcome(
            principal(authorization),
            action_id=action_id,
            event_key=body["event_key"],
            status=body["status"],
            evidence=body.get("evidence") or [],
            reason_code=body["reason_code"],
            lease_id=body.get("lease_id"),
        )
        return _record_json(record)

    return app

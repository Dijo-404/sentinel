"""FastAPI surface for merchant-comms.v1 draft lifecycle."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from sentinel_merchant_comms import CONTRACT_VERSION, PORT, __version__
from sentinel_merchant_comms.adapters.auth import TokenMapAuth
from sentinel_merchant_comms.application.errors import MerchantCommsError
from sentinel_merchant_comms.application.service import MerchantCommsService
from sentinel_merchant_comms.domain.types import (
    DraftCreateRequest,
    DraftDecisionRequest,
    SimulateSendRequest,
)


def create_app(
    *,
    service: MerchantCommsService,
    auth: TokenMapAuth,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-comms", version=__version__)
    app.state.service = service
    app.state.auth = auth
    app.state.mode = mode

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        return {"status": "ready", "mode": mode, "port": PORT}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": "merchant-comms",
            "port": PORT,
            "mode": mode,
        }

    @app.post("/v1/drafts")
    def create_draft(
        body: DraftCreateRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal = auth.authenticate(authorization)
        draft = service.create_draft(
            case_id=body.case_id,
            language=body.language,
            principal=principal,
            channel=body.channel,
        )
        return draft.model_dump(exclude_none=True)

    @app.get("/v1/drafts/{draft_id}")
    def get_draft(
        draft_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal = auth.authenticate(authorization)
        draft = service.get_draft(draft_id, principal)
        return draft.model_dump(exclude_none=True)

    @app.post("/v1/drafts/{draft_id}/decisions")
    def decide(
        draft_id: str,
        body: DraftDecisionRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal = auth.authenticate(authorization)
        draft = service.decide(draft_id=draft_id, decision=body.decision, principal=principal)
        return draft.model_dump(exclude_none=True)

    @app.post("/v1/drafts/{draft_id}/simulate-send")
    def simulate_send(
        draft_id: str,
        body: SimulateSendRequest | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal = auth.authenticate(authorization)
        channel = body.channel if body is not None else None
        draft = service.simulate_send(draft_id=draft_id, principal=principal, channel=channel)
        return draft.model_dump(exclude_none=True)

    @app.exception_handler(MerchantCommsError)
    async def merchant_error(_request: Request, exc: MerchantCommsError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": f"req-{uuid.uuid4().hex[:10]}",
            },
        )

    return app

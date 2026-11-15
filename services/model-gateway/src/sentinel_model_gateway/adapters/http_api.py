"""FastAPI boundary: `POST /v1/proposals` (workflow) and `POST /v1/replies` (assistant)."""

from __future__ import annotations

import hmac
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..application.errors import GatewayError, UnauthorizedError
from ..application.service import ProposalService, ReplyService
from ..domain.types import ModelRequest

# A real Sarvam call produced the reply text, so it is labeled live inference.
REPLY_EVIDENCE_MODE = "live"


@dataclass
class AppServices:
    proposals: ProposalService
    replies: ReplyService
    proposal_tokens: frozenset[str]
    model: str


def _error(code: str, message: str, status: int, request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
    return JSONResponse(
        {"code": code, "message": message, "request_id": request_id}, status_code=status
    )


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-model-gateway", version="0.1.0")

    @app.exception_handler(GatewayError)
    def _gateway_error(request: Request, exc: GatewayError) -> JSONResponse:
        return _error(exc.code, exc.message, exc.http_status, request)

    def require_bearer(authorization: Annotated[str | None, Header()] = None) -> None:
        token = (authorization or "").removeprefix("Bearer ").strip()
        if not authorization or not authorization.startswith("Bearer ") or not token:
            raise UnauthorizedError("Missing bearer token")
        if not any(hmac.compare_digest(token, t) for t in services.proposal_tokens):
            raise UnauthorizedError("Unknown bearer token")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "component": "model-gateway",
            "provider": "sarvam",
            "model": services.model,
            "routes": ["/v1/proposals", "/v1/replies"],
            "financial_authority": False,
        }

    @app.post("/v1/proposals", dependencies=[Depends(require_bearer)])
    def proposals(request: Request, body: Annotated[dict[str, Any], Body()]) -> JSONResponse:
        try:
            model_request = ModelRequest.model_validate(body)
        except ValidationError as exc:
            return _error(
                "VALIDATION_ERROR",
                f"invalid ModelRequest: {exc.error_count()} errors",
                422,
                request,
            )
        result = services.proposals.propose(model_request)
        return JSONResponse(result.model_dump(exclude_none=True))

    @app.post("/v1/replies")
    def replies(request: Request, body: Annotated[dict[str, Any], Body()]) -> JSONResponse:
        # shortcut: unauthenticated because the assistant's HttpModelReply sends no bearer;
        # add auth here once that caller sends one. Keep the gateway on a private network.
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            return _error("VALIDATION_ERROR", "text is required", 422, request)
        reply = services.replies.reply(text.strip())
        return JSONResponse({"text": reply, "evidence_mode": REPLY_EVIDENCE_MODE})

    return app

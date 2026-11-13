"""FastAPI adapter for merchant-inbox.v1 routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_merchant_inbox.adapters.auth import TokenMap
from sentinel_merchant_inbox.application.service import MerchantInboxService
from sentinel_merchant_inbox.contracts import COMPONENT, CONTRACT_VERSION, PORT
from sentinel_merchant_inbox.domain.errors import InboxError


def create_app(
    *,
    service: MerchantInboxService,
    tokens: TokenMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-inbox", version="0.1.0")
    app.state.service = service
    app.state.tokens = tokens
    app.state.mode = mode

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready", "mode": app.state.mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": app.state.mode,
            "port": PORT,
        }

    @app.get("/v1/exceptions")
    def list_exceptions(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        binding = _auth(app, request, request_id)
        if isinstance(binding, JSONResponse):
            return binding
        merchant_ref = request.query_params.get("merchant_ref") or ""
        try:
            items = app.state.service.list_exceptions(
                binding,
                merchant_ref=merchant_ref,
                kind=request.query_params.get("kind"),
                status=request.query_params.get("status"),
            )
        except InboxError as exc:
            return _error(exc, request_id)
        return JSONResponse(
            status_code=200,
            content={"items": [item.as_dict() for item in items]},
        )

    @app.get("/v1/exceptions/{item_id}")
    def get_exception(item_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        binding = _auth(app, request, request_id)
        if isinstance(binding, JSONResponse):
            return binding
        try:
            body = app.state.service.get_exception(binding, item_id=item_id)
        except InboxError as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=body)

    @app.post("/v1/exceptions/{item_id}/assign")
    async def assign(item_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        binding = _auth(app, request, request_id)
        if isinstance(binding, JSONResponse):
            return binding
        payload = await _json_body(request, request_id)
        if isinstance(payload, JSONResponse):
            return payload
        try:
            item = app.state.service.assign(
                binding,
                item_id=item_id,
                assignee=str(payload.get("assignee") or ""),
            )
        except InboxError as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=item.as_dict())

    @app.post("/v1/exceptions/{item_id}/notes")
    async def add_note(item_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        binding = _auth(app, request, request_id)
        if isinstance(binding, JSONResponse):
            return binding
        payload = await _json_body(request, request_id)
        if isinstance(payload, JSONResponse):
            return payload
        try:
            item = app.state.service.add_note(
                binding,
                item_id=item_id,
                note=str(payload.get("note") or ""),
            )
        except InboxError as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=item.as_dict())

    @app.post("/v1/exceptions/{item_id}/escalate")
    async def escalate(item_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        binding = _auth(app, request, request_id)
        if isinstance(binding, JSONResponse):
            return binding
        payload = await _json_body(request, request_id)
        if isinstance(payload, JSONResponse):
            return payload
        try:
            body = app.state.service.escalate(
                binding,
                item_id=item_id,
                reason_code=str(payload.get("reason_code") or ""),
                owner_queue=str(payload.get("owner_queue") or "SUPERVISOR"),
            )
        except InboxError as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=body)

    return app


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _auth(app: FastAPI, request: Request, request_id: str):
    binding = app.state.tokens.resolve(request.headers.get("authorization"))
    if binding is None:
        return JSONResponse(
            status_code=401,
            content={
                "code": "UNAUTHORIZED",
                "message": "Valid bearer token required",
                "request_id": request_id,
            },
        )
    return binding


async def _json_body(request: Request, request_id: str) -> dict[str, Any] | JSONResponse:
    try:
        body: Any = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_INPUT",
                "message": "Body must be JSON",
                "request_id": request_id,
            },
        )
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_INPUT",
                "message": "Body must be a JSON object",
                "request_id": request_id,
            },
        )
    return body


def _error(exc: InboxError, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "request_id": request_id},
    )

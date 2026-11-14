"""FastAPI boundary for assistant.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import AssistantError, ValidationError
from ..application.service import AssistantService
from ..domain.types import COMPONENT, CONTRACT_VERSION, PORT_NAME
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    assistant: AssistantService
    mode: str
    component: str = COMPONENT


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-assistant", version="0.1.0")
    app.state.services = services

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict:
        return {"status": "ready", "mode": services.mode}

    @app.get("/v1/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": services.component,
            "mode": services.mode,
            "port": PORT_NAME,
            "financial_authority": False,
        }

    @app.get("/v1/threads")
    def list_threads(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            role = request.query_params.get("role")
            if role is None or role == "":
                raise ValidationError("role query parameter is required")
            items = services.assistant.list_threads(principal, role=role)
            return JSONResponse({"threads": [item.to_wire() for item in items]})
        except AssistantError as exc:
            return _error(exc, request_id)

    @app.post("/v1/threads")
    async def create_thread(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_body(request)
            title = body.get("title") if isinstance(body.get("title"), str) else None
            thread = services.assistant.create_thread(principal, title=title)
            return JSONResponse(thread.to_wire())
        except AssistantError as exc:
            return _error(exc, request_id)

    @app.get("/v1/threads/{thread_id}/messages")
    def list_messages(thread_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            items = services.assistant.list_messages(principal, thread_id=thread_id)
            return JSONResponse({"messages": [item.to_wire() for item in items]})
        except AssistantError as exc:
            return _error(exc, request_id)

    @app.post("/v1/threads/{thread_id}/messages")
    async def post_message(thread_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_body(request)
            text = body.get("text") if isinstance(body.get("text"), str) else ""
            message = services.assistant.post_message(principal, thread_id=thread_id, text=text)
            return JSONResponse(message.to_wire())
        except AssistantError as exc:
            return _error(exc, request_id)

    return app


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 — map parse failures to validation
        raise ValidationError("Request body must be JSON object") from exc
    if not isinstance(body, dict):
        raise ValidationError("Request body must be JSON object")
    return body


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: AssistantError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

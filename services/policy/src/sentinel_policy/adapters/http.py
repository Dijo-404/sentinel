"""FastAPI adapter for policy.v1 routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_policy.adapters.auth import TokenMap
from sentinel_policy.application.evaluate import EvaluatePolicy
from sentinel_policy.contracts import (
    COMPONENT,
    CONTRACT_VERSION,
    PORT,
    PolicyInputError,
    parse_policy_request,
)


def create_app(
    *,
    evaluate: EvaluatePolicy,
    tokens: TokenMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-policy", version="0.1.0")
    app.state.evaluate = evaluate
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

    @app.post("/v1/evaluate")
    async def evaluate_route(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal = app.state.tokens.resolve(request.headers.get("authorization"))
        if principal is None:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "UNAUTHORIZED",
                    "message": "Valid bearer token required",
                    "request_id": request_id,
                },
            )
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
        try:
            policy_request = parse_policy_request(body)
            result = app.state.evaluate(principal, policy_request)
        except PolicyInputError as exc:
            return JSONResponse(
                status_code=422,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                },
            )
        return JSONResponse(status_code=200, content=result.as_dict())

    return app

"""FastAPI surface for context POST /v1/proposals."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from sentinel_indic_context import CONTRACT_VERSION, PORT, __version__
from sentinel_indic_context.adapters.auth import TokenMapAuth
from sentinel_indic_context.application.errors import IndicContextError
from sentinel_indic_context.application.service import IndicContextService
from sentinel_indic_context.domain.types import ModelRequest


def create_app(
    *,
    service: IndicContextService,
    auth: TokenMapAuth,
    mode: str = "fake",
) -> FastAPI:
    app = FastAPI(title="sentinel-indic-context", version=__version__)
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
            "component": "indic-context",
            "port": PORT,
            "mode": mode,
        }

    @app.post("/v1/proposals")
    def proposals(
        body: ModelRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal = auth.authenticate(authorization)
        result, report, _normalized = service.propose(body, principal)
        return {
            **result.model_dump(exclude_none=True),
            "inference_report": report.model_dump(exclude_none=True),
        }

    @app.exception_handler(IndicContextError)
    async def indic_error(_request: Request, exc: IndicContextError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": f"req-{uuid.uuid4().hex[:10]}",
            },
        )

    return app

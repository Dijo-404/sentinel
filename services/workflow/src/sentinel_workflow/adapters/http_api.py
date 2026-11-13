"""FastAPI surface for workflow.v1."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from sentinel_workflow import CONTRACT_VERSION, __version__
from sentinel_workflow.adapters.auth import TokenMapAuth
from sentinel_workflow.application.errors import WorkflowError
from sentinel_workflow.application.service import WorkflowService, authorize_run
from sentinel_workflow.domain.types import Ack, WorkflowRequest


def create_app(
    *,
    service: WorkflowService,
    auth: TokenMapAuth,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-workflow", version=__version__)
    app.state.service = service
    app.state.auth = auth
    app.state.mode = mode

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, Any]:
        return {"status": "ready", "mode": mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": "workflow",
            "mode": mode,
        }

    @app.post("/v1/runs", status_code=202, response_model=Ack)
    def runs(
        body: WorkflowRequest,
        authorization: str | None = Header(default=None),
    ) -> Ack:
        principal = auth.authenticate(authorization)
        authorize_run(principal, body.case_id)
        # DECISION resume approval comes from ledger.get_action(...).approval only.
        return service.accept(body, principal)

    @app.exception_handler(WorkflowError)
    async def workflow_error(_request: Request, exc: WorkflowError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": f"req-{uuid.uuid4().hex[:10]}",
            },
        )

    return app

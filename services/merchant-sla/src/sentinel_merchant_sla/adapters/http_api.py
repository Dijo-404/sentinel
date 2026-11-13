"""FastAPI adapter for merchant-sla.v1 routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_merchant_sla.adapters.auth import TokenMap
from sentinel_merchant_sla.application.errors import AppError
from sentinel_merchant_sla.application.service import MerchantSlaService
from sentinel_merchant_sla.contracts import (
    COMPONENT,
    CONTRACT_VERSION,
    PORT,
    SlaInputError,
)


def create_app(
    *,
    service: MerchantSlaService,
    tokens: TokenMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-sla", version="0.1.0")
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

    def _auth(request: Request, request_id: str) -> Any:
        principal = app.state.tokens.resolve(request.headers.get("authorization"))
        if principal is None:
            return None, JSONResponse(
                status_code=401,
                content={
                    "code": "UNAUTHORIZED",
                    "message": "Valid bearer token required",
                    "request_id": request_id,
                },
            )
        return principal, None

    def _error(exc: Exception, request_id: str) -> JSONResponse:
        if isinstance(exc, SlaInputError):
            status = 409 if exc.code == "CONFLICT" else 422
            return JSONResponse(
                status_code=status,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                },
            )
        if isinstance(exc, AppError):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                },
            )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL",
                "message": "unexpected error",
                "request_id": request_id,
            },
        )

    async def _json_body(request: Request, request_id: str) -> tuple[Any, JSONResponse | None]:
        try:
            return await request.json(), None
        except Exception:
            return None, JSONResponse(
                status_code=422,
                content={
                    "code": "INVALID_INPUT",
                    "message": "Body must be JSON",
                    "request_id": request_id,
                },
            )

    @app.post("/v1/policies")
    async def create_policy(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        body, body_err = await _json_body(request, request_id)
        if body_err is not None:
            return body_err
        try:
            policy = app.state.service.upsert_policy(principal, body)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=policy.as_dict())

    @app.get("/v1/policies/{policy_id}")
    def get_policy(policy_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        try:
            policy = app.state.service.get_policy(principal, policy_id)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=policy.as_dict())

    @app.get("/v1/policies")
    def list_policies(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        merchant_ref = request.query_params.get("merchant_ref")
        if not merchant_ref:
            return JSONResponse(
                status_code=422,
                content={
                    "code": "INVALID_INPUT",
                    "message": "merchant_ref query required",
                    "request_id": request_id,
                },
            )
        try:
            policies = app.state.service.list_policies(principal, merchant_ref)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(
            status_code=200,
            content={"policies": [p.as_dict() for p in policies]},
        )

    @app.post("/v1/tasks")
    async def create_task(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        body, body_err = await _json_body(request, request_id)
        if body_err is not None:
            return body_err
        try:
            task = app.state.service.create_task(principal, body)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    @app.get("/v1/tasks/{task_id}")
    def get_task(task_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        try:
            task = app.state.service.get_task(principal, task_id)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    @app.get("/v1/tasks")
    def list_tasks(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        overdue_only = request.query_params.get("overdue_only", "").lower() in {
            "1",
            "true",
            "yes",
        }
        try:
            tasks = app.state.service.list_tasks(
                principal,
                merchant_ref=request.query_params.get("merchant_ref"),
                case_id=request.query_params.get("case_id"),
                overdue_only=overdue_only,
            )
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content={"tasks": [t.as_dict() for t in tasks]})

    @app.post("/v1/tasks/{task_id}/assign")
    async def assign_task(task_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        body, body_err = await _json_body(request, request_id)
        if body_err is not None:
            return body_err
        try:
            task = app.state.service.assign_task(principal, task_id, body)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    @app.post("/v1/tasks/{task_id}/follow-ups")
    async def schedule_follow_up(task_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        body, body_err = await _json_body(request, request_id)
        if body_err is not None:
            return body_err
        try:
            task = app.state.service.schedule_follow_up(principal, task_id, body)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    @app.post("/v1/tasks/{task_id}/escalate")
    async def escalate_task(task_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        body, body_err = await _json_body(request, request_id)
        if body_err is not None:
            return body_err
        try:
            task = app.state.service.escalate_task(principal, task_id, body)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    @app.post("/v1/tasks/{task_id}/complete")
    async def complete_task(task_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal, err = _auth(request, request_id)
        if err is not None:
            return err
        try:
            task = app.state.service.complete_task(principal, task_id)
        except (SlaInputError, AppError) as exc:
            return _error(exc, request_id)
        return JSONResponse(status_code=200, content=task.as_dict())

    return app

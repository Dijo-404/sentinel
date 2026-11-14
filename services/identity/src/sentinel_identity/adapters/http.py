"""FastAPI boundary for identity.v1 auth + admin routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import IdentityError, ValidationError
from ..application.service import IdentityService
from ..domain.roles import CONTRACT_VERSION


@dataclass
class AppServices:
    identity: IdentityService
    mode: str
    component: str = "identity"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-identity", version="0.1.0")
    app.state.services = services

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict:
        return {"status": "ready", "mode": services.mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": services.component,
            "mode": services.mode,
            "money_authority": False,
        }

    # --- §12.1 Auth ---

    @app.post("/v1/auth/customer/register")
    async def register(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            allowed = {"email", "password", "display_name", "preferred_language"}
            extra = {k: v for k, v in body.items() if k not in allowed}
            # Keep preferred_language as non-privileged optional; strip before domain.
            result = services.identity.register_customer(
                email=str(body.get("email", "")),
                password=str(body.get("password", "")),
                display_name=str(body.get("display_name", "")),
                extra=extra,
                request_id=request_id,
            )
            return JSONResponse(result, status_code=201)
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/auth/login")
    async def login(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            result = services.identity.login(
                email=str(body.get("email", "")),
                password=str(body.get("password", "")),
                requested_role=body.get("requested_role"),
                request_id=request_id,
            )
            return JSONResponse(result)
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/auth/logout")
    def logout(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            token = _bearer(request)
            result = services.identity.logout(session_token=token, request_id=request_id)
            return JSONResponse(result)
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/auth/me")
    def me(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            token = _bearer(request)
            forged = {
                k.lower(): v
                for k, v in request.headers.items()
                if k.lower() in {"x-role", "x-sentinel-role", "x-tenant-id", "x-sentinel-tenant"}
            }
            return JSONResponse(
                services.identity.me(session_token=token, forged_headers=forged or None)
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/auth/workspaces")
    def workspaces(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(services.identity.list_workspaces(session_token=_bearer(request)))
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/auth/workspaces/select")
    async def select_workspace(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            assignment_id = body.get("assignment_id")
            if not assignment_id:
                raise ValidationError("assignment_id is required")
            return JSONResponse(
                services.identity.select_workspace(
                    session_token=_bearer(request),
                    assignment_id=str(assignment_id),
                    request_id=request_id,
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/auth/accept-invitation")
    async def accept_invitation(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            return JSONResponse(
                services.identity.accept_invitation(
                    token=str(body.get("token", "")),
                    email=str(body.get("email", "")),
                    password=str(body.get("password", "")),
                    display_name=body.get("display_name"),
                    request_id=request_id,
                ),
                status_code=201,
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/merchant-memberships")
    def merchant_memberships(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            tenant_id = request.query_params.get("tenant_id") or ""
            merchant_ref = request.query_params.get("merchant_ref") or ""
            return JSONResponse(
                services.identity.list_merchant_memberships(
                    session_token=_bearer(request),
                    tenant_id=str(tenant_id),
                    merchant_ref=str(merchant_ref),
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    # --- §12.2 Admin ---

    @app.get("/v1/admin/users")
    def admin_list_users(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(services.identity.admin_list_users(session_token=_bearer(request)))
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/invitations")
    async def admin_invite(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            if "granted_by" in body:
                raise ValidationError("granted_by must not be client-supplied")
            return JSONResponse(
                services.identity.admin_invite(
                    session_token=_bearer(request),
                    display_name=str(body.get("display_name", "")),
                    work_email=str(body.get("work_email", "")),
                    tenant_id=str(body.get("tenant_id", "")),
                    role_id=str(body.get("role_id", "")),
                    reason=body.get("reason"),
                    idempotency_key=body.get("idempotency_key"),
                    scope=body.get("scope") if isinstance(body.get("scope"), dict) else None,
                    request_id=request_id,
                ),
                status_code=201,
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/admin/invitations")
    def admin_list_invitations(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_list_invitations(session_token=_bearer(request))
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/invitations/{invitation_id}/revoke")
    def admin_revoke_invitation(invitation_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_revoke_invitation(
                    session_token=_bearer(request),
                    invitation_id=invitation_id,
                    request_id=request_id,
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/users/{user_id}/roles")
    async def admin_grant(user_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            return JSONResponse(
                services.identity.admin_grant_role(
                    session_token=_bearer(request),
                    user_id=user_id,
                    tenant_id=str(body.get("tenant_id", "")),
                    role_id=str(body.get("role_id", "")),
                    merchant_ref=body.get("merchant_ref"),
                    team_id=body.get("team_id"),
                    request_id=request_id,
                ),
                status_code=201,
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.delete("/v1/admin/users/{user_id}/roles/{assignment_id}")
    def admin_revoke_role(user_id: str, assignment_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_revoke_role(
                    session_token=_bearer(request),
                    user_id=user_id,
                    assignment_id=assignment_id,
                    request_id=request_id,
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/users/{user_id}/suspend")
    def admin_suspend(user_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_suspend(
                    session_token=_bearer(request), user_id=user_id, request_id=request_id
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/users/{user_id}/reactivate")
    def admin_reactivate(user_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_reactivate(
                    session_token=_bearer(request), user_id=user_id, request_id=request_id
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/admin/roles")
    def admin_roles(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(services.identity.admin_list_roles(session_token=_bearer(request)))
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.get("/v1/admin/audit-events")
    def admin_audit(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(services.identity.admin_list_audit(session_token=_bearer(request)))
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/users/{user_id}/sessions/revoke")
    def admin_revoke_sessions(user_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            return JSONResponse(
                services.identity.admin_revoke_sessions(
                    session_token=_bearer(request), user_id=user_id, request_id=request_id
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    @app.post("/v1/admin/privileged-changes/{change_id}/decision")
    async def admin_privileged_decision(change_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            body = await _json_object(request)
            return JSONResponse(
                services.identity.admin_decide_privileged_change(
                    session_token=_bearer(request),
                    change_id=change_id,
                    decision=str(body.get("decision", "")),
                    reason=body.get("reason"),
                    request_id=request_id,
                )
            )
        except IdentityError as exc:
            return _error(exc, request_id)

    # --- Sandbox invitation delivery (local demo inbox; not production email) ---

    @app.post("/v1/sandbox/delivery/drain")
    def sandbox_delivery_drain() -> dict:
        return services.identity.flush_delivery_outbox()

    @app.get("/v1/sandbox/inbox")
    def sandbox_inbox(request: Request) -> dict:
        email = request.query_params.get("email")
        return services.identity.list_sandbox_inbox(work_email=email or None)

    return app


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        from ..application.errors import UnauthorizedError

        raise UnauthorizedError("Bearer session required")
    return header.split(" ", 1)[1].strip()


async def _json_object(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception as exc:
        raise ValidationError("Request body must be JSON object") from exc
    if not isinstance(body, dict):
        raise ValidationError("Request body must be JSON object")
    return body


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _error(exc: IdentityError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {"code": exc.code, "message": exc.message, "request_id": request_id},
        status_code=exc.http_status,
    )

"""FastAPI boundary for merchant-teams.v1 routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import TeamsError, ValidationError
from ..application.staff import StaffService
from ..domain.types import CONTRACT_VERSION
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    staff: StaffService
    mode: str
    component: str = "merchant-teams"


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-merchant-teams", version="0.1.0")
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
        }

    @app.post("/v1/staff")
    async def create_staff(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            allowed = {
                "merchant_ref",
                "display_name",
                "roles",
                "approval_limit_minor",
                "currency",
                "staff_id",
            }
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("merchant_ref", "display_name", "roles"):
                if key not in body:
                    raise ValidationError(f"{key} is required")
            staff = services.staff.create(
                principal,
                merchant_ref=body["merchant_ref"],
                display_name=body["display_name"],
                roles=body["roles"],
                approval_limit_minor=body.get("approval_limit_minor"),
                currency=body.get("currency"),
                staff_id=body.get("staff_id"),
            )
            return JSONResponse(staff.to_wire(), status_code=201)
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.get("/v1/staff")
    def list_staff(request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            merchant_ref = request.query_params.get("merchant_ref")
            if not merchant_ref:
                raise ValidationError("merchant_ref query is required")
            rows = services.staff.list_staff(principal, merchant_ref)
            return JSONResponse({"staff": [row.to_wire() for row in rows]})
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.post("/v1/staff/sync")
    async def sync_memberships(request: Request) -> JSONResponse:
        """Project authoritative identity.v1 memberships into the local store."""
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            if set(body) - {"merchant_ref"}:
                raise ValidationError("Undeclared fields are not permitted")
            merchant_ref = body.get("merchant_ref")
            if not merchant_ref or not isinstance(merchant_ref, str):
                raise ValidationError("merchant_ref is required")
            rows = services.staff.sync_memberships(principal, merchant_ref)
            return JSONResponse({"staff": [row.to_wire() for row in rows]})
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.get("/v1/merchant/team")
    def merchant_team(request: Request) -> JSONResponse:
        """Membership projection surface.

        Auto-syncs from identity when configured; always labels the list as a
        projection (not a grant authority).
        """
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            merchant_ref = request.query_params.get("merchant_ref")
            if not merchant_ref:
                raise ValidationError("merchant_ref query is required")
            rows, source = services.staff.list_team(principal, merchant_ref)
            return JSONResponse(
                {
                    "staff": [row.to_wire() for row in rows],
                    "source": source,
                }
            )
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.get("/v1/merchant/settings")
    def merchant_settings(request: Request) -> JSONResponse:
        """Merchant business preferences. Missing row fails closed (404)."""
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            merchant_ref = request.query_params.get("merchant_ref")
            if not merchant_ref:
                raise ValidationError("merchant_ref query is required")
            row = services.staff.get_settings(principal, merchant_ref)
            return JSONResponse(row.to_wire())
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.get("/v1/staff/{staff_id}")
    def get_staff(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            staff = services.staff.get(principal, staff_id)
            return JSONResponse(staff.to_wire())
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.patch("/v1/staff/{staff_id}")
    async def update_staff(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            allowed = {
                "display_name",
                "roles",
                "approval_limit_minor",
                "currency",
                "clear_approval_limit",
            }
            if set(body) - allowed:
                raise ValidationError("Undeclared fields are not permitted")
            if not body:
                raise ValidationError("At least one field is required")
            staff = services.staff.update(
                principal,
                staff_id,
                display_name=body.get("display_name"),
                roles=body.get("roles"),
                approval_limit_minor=body.get("approval_limit_minor"),
                currency=body.get("currency"),
                clear_approval_limit=bool(body.get("clear_approval_limit", False)),
            )
            return JSONResponse(staff.to_wire())
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.post("/v1/staff/{staff_id}/deactivate")
    def deactivate_staff(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            staff = services.staff.deactivate(principal, staff_id)
            return JSONResponse(staff.to_wire())
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.get("/v1/staff/{staff_id}/activity")
    def list_activity(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            events = services.staff.list_activity(principal, staff_id)
            return JSONResponse({"events": [event.to_wire() for event in events]})
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.post("/v1/staff/{staff_id}/activity")
    async def record_activity(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            if set(body) - {"kind", "subject_ref", "summary"}:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("kind", "subject_ref", "summary"):
                if key not in body:
                    raise ValidationError(f"{key} is required")
            event = services.staff.record_activity(
                principal,
                staff_id,
                kind=body["kind"],
                subject_ref=body["subject_ref"],
                summary=body["summary"],
            )
            return JSONResponse(event.to_wire(), status_code=201)
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.post("/v1/staff/{staff_id}/advisory-check")
    async def advisory_check(staff_id: str, request: Request) -> JSONResponse:
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            if set(body) - {"amount_minor", "currency"}:
                raise ValidationError("Undeclared fields are not permitted")
            for key in ("amount_minor", "currency"):
                if key not in body:
                    raise ValidationError(f"{key} is required")
            result = services.staff.advisory_check(
                principal,
                staff_id,
                amount_minor=body["amount_minor"],
                currency=body["currency"],
            )
            return JSONResponse(result.to_wire())
        except TeamsError as exc:
            return _error(exc, request_id)

    @app.post("/v1/staff/{staff_id}/authorize")
    async def authorize_money(staff_id: str, request: Request) -> JSONResponse:
        """Always fails closed: advisory limits never authorize money."""
        request_id = _request_id(request)
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            body = await _json_object(request)
            services.staff.authorize_money(
                principal,
                staff_id,
                amount_minor=int(body.get("amount_minor", 0) or 0),
                currency=str(body.get("currency", "")),
            )
            return JSONResponse(
                {"code": "UNEXPECTED", "message": "unreachable", "request_id": request_id},
                status_code=500,
            )
        except TeamsError as exc:
            return _error(exc, request_id)

    return app


async def _json_object(request: Request) -> dict:
    body = await request.json()
    if not isinstance(body, dict):
        raise ValidationError("JSON object required")
    return body


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"


def _error(exc: TeamsError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )

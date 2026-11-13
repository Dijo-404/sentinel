from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from sentinel_simulator.application.service import PaymentSimulator
from sentinel_simulator.domain.rules import (
    DomainError,
    IdempotencyConflict,
    NotFound,
    TimeoutAfterAccept,
    Unauthorized,
    Unavailable,
    ValidationError,
    assert_refund_request,
)

from .auth import TokenMap

CONTRACT_VERSION = "sentinel.task-contracts.v1"
COMPONENT = "sentinel-simulator"


def _error(code: str, message: str, status: int, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "request_id": request_id},
    )


def _request_id(request: Request) -> str:
    header = request.headers.get("x-request-id")
    return header if header else f"req-{uuid.uuid4().hex[:12]}"


def _map_error(exc: DomainError, request_id: str) -> JSONResponse:
    if isinstance(exc, Unauthorized):
        return _error(exc.code, exc.message, 403, request_id)
    if isinstance(exc, NotFound):
        return _error(exc.code, exc.message, 404, request_id)
    if isinstance(exc, IdempotencyConflict):
        return _error(exc.code, exc.message, 409, request_id)
    if isinstance(exc, Unavailable):
        return _error(exc.code, exc.message, 503, request_id)
    if isinstance(exc, ValidationError):
        return _error(exc.code, exc.message, 422, request_id)
    return _error(exc.code, exc.message, 400, request_id)


def mount_routes(
    app: FastAPI,
    *,
    simulator: PaymentSimulator,
    tokens: TokenMap,
    mode: str = "fixture",
    payment_provider: str = "simulator",
) -> None:
    resolved_mode = mode if mode in {"fixture", "real-peers"} else "fixture"

    def principal_from(request: Request):
        return tokens.resolve(request.headers.get("authorization"))

    def maybe_delay() -> None:
        delay_ms = simulator.delay_ms()
        if delay_ms:
            time.sleep(delay_ms / 1000.0)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        # evidence_mode stays fixture/synthetic; never claim live rails.
        return {
            "status": "ready",
            "mode": resolved_mode,
            "evidence_mode": "fixture",
            "payment_provider": payment_provider,
        }

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": resolved_mode,
        }

    @app.get("/v1/transactions")
    def transactions(request: Request, order_reference: str) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            payments = simulator.list_transactions(principal_from(request), order_reference)
            return {"payments": [payment.to_dict() for payment in payments]}
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/orders/{order_reference}")
    def orders(order_reference: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            return simulator.get_order(principal_from(request), order_reference).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/refunds")
    def refunds_query(request: Request, transaction_ref: str) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            refunds = simulator.list_refunds(principal_from(request), transaction_ref)
            return {"refunds": [refund.to_dict() for refund in refunds]}
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/refunds")
    async def create_refund(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("request body must be a JSON object")
            refund_request = assert_refund_request(body, request.headers.get("idempotency-key"))
            refund = simulator.create_refund(principal_from(request), refund_request)
            return JSONResponse(status_code=202, content=refund.to_dict())
        except TimeoutAfterAccept as exc:
            return _error(exc.code, exc.message, 504, request_id)
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/refunds/{provider_ref}")
    def refund_by_ref(provider_ref: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            return simulator.get_refund(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/credits/{provider_ref}")
    def credit_by_ref(provider_ref: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            maybe_delay()
            return simulator.get_credit(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/settlements/{provider_ref}")
    def settlement_by_ref(provider_ref: str, request: Request) -> Any:
        """ProviderAdapter settlement/credit evidence surface (alias of credits)."""
        request_id = _request_id(request)
        try:
            maybe_delay()
            return simulator.get_settlement(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/admin/faults")
    def get_faults(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.get_faults(principal_from(request)).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.put("/v1/admin/faults")
    async def put_faults(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("request body must be a JSON object")
            return simulator.set_faults(principal_from(request), body).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/faults/reset")
    def reset_faults(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.reset_faults(principal_from(request)).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/faults/schedules/{name}")
    def apply_fault_schedule(name: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.apply_fault_schedule(principal_from(request), name).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/seeds/{pack}")
    def load_seed_pack(pack: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.load_seed_pack(principal_from(request), pack)
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/demo-reset")
    def demo_reset(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.demo_reset(principal_from(request))
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/webhooks/emit")
    async def emit_webhook(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValidationError("request body must be a JSON object")
            provider_ref = body.get("provider_ref")
            if not isinstance(provider_ref, str) or not provider_ref:
                raise ValidationError("provider_ref must be a nonempty string")
            event_type = body.get("type", "REFUND_STATUS")
            if not isinstance(event_type, str):
                raise ValidationError("type must be a string")
            return simulator.emit_signed_webhook(
                principal_from(request),
                provider_ref=provider_ref,
                event_type=event_type,
            )
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/admin/refunds/{provider_ref}/stats")
    def refund_stats(provider_ref: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.refund_stats(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/refunds/{provider_ref}/confirm")
    def confirm_refund(provider_ref: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.confirm_refund(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.post("/v1/admin/credits/{provider_ref}/confirm")
    def confirm_credit(provider_ref: str, request: Request) -> Any:
        request_id = _request_id(request)
        try:
            return simulator.confirm_credit(principal_from(request), provider_ref).to_dict()
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.get("/v1/admin/events")
    def list_events(request: Request) -> Any:
        request_id = _request_id(request)
        try:
            events = simulator.list_events(principal_from(request))
            return {"events": [event.to_dict() for event in events]}
        except DomainError as exc:
            return _map_error(exc, request_id)

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = _request_id(request)
        return response

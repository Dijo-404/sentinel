"""FastAPI surface for verifier.v1."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

from sentinel_verifier import COMPONENT, CONTRACT_SHA256, CONTRACT_VERSION, __version__
from sentinel_verifier.adapters.auth_tokens import TokenPrincipalMap
from sentinel_verifier.application.service import VerifierService
from sentinel_verifier.domain.errors import ValidationError, VerifierError
from sentinel_verifier.domain.types import VerificationRequest


def create_app(
    *,
    service: VerifierService,
    auth: TokenPrincipalMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-verifier", version=__version__)
    app.state.service = service
    app.state.auth = auth
    app.state.mode = mode

    @app.exception_handler(VerifierError)
    async def verifier_error(request: Request, exc: VerifierError) -> JSONResponse:
        request_id = request.headers.get("x-request-id", "request-local")
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "request_id": request_id},
        )

    def principal(authorization: str | None):
        return auth.resolve(authorization)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        label = "fixture-ready" if mode == "fixture" else "real-peers-ready"
        return {"status": label}

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": mode,
            "port": "verifier.v1",
            "contract_sha256": CONTRACT_SHA256,
        }

    @app.post("/v1/rechecks", status_code=202)
    def rechecks(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency-Key required")
        request = VerificationRequest.from_mapping(body)
        ack = service.schedule_recheck(
            principal(authorization),
            request,
            idempotency_key=idempotency_key,
        )
        return JSONResponse(status_code=202, content=ack.as_dict())

    @app.post("/v1/webhooks/simulator", status_code=202)
    async def webhook_simulator(
        request: Request,
        x_sentinel_signature: str | None = Header(default=None, alias="X-Sentinel-Signature"),
    ):
        raw = await request.body()
        result = service.ingest_webhook(raw_body=raw, signature=x_sentinel_signature)
        return JSONResponse(status_code=202, content=result)

    @app.post("/v1/assessments")
    def assessments(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ):
        request = VerificationRequest.from_mapping(body)
        result = service.create_assessment(principal(authorization), request)
        return result.as_dict()

    @app.get("/v1/assessments/{assessment_id}")
    def get_assessment(
        assessment_id: str,
        authorization: str | None = Header(default=None),
    ):
        result = service.get_assessment(principal(authorization), assessment_id)
        return result.as_dict()

    @app.api_route("/v1/webhooks/simulator", methods=["GET", "PUT", "PATCH", "DELETE"])
    def webhook_method_not_allowed() -> Response:
        return Response(status_code=405)

    return app

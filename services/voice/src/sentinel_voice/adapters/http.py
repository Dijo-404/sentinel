"""FastAPI adapter for voice.v1 routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentinel_voice.adapters.auth import TokenMap
from sentinel_voice.adapters.redaction import contains_secret, redact_secrets
from sentinel_voice.application.speak import SpeakVoice
from sentinel_voice.application.transcribe import TranscribeVoice
from sentinel_voice.contracts import (
    COMPONENT,
    CONTRACT_VERSION,
    PORT,
    VoiceConsentError,
    VoiceForbiddenError,
    VoiceInputError,
    VoiceProviderError,
    parse_speak_request,
    parse_voice_request,
)
from sentinel_voice.domain import reason_codes as rc

logger = logging.getLogger("sentinel_voice")


def create_app(
    *,
    transcribe: TranscribeVoice,
    speak: SpeakVoice,
    tokens: TokenMap,
    mode: str = "fixture",
) -> FastAPI:
    app = FastAPI(title="sentinel-voice", version="0.1.0")
    app.state.transcribe = transcribe
    app.state.speak = speak
    app.state.tokens = tokens
    app.state.mode = mode

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        body = {"status": "ready", "mode": app.state.mode}
        if app.state.mode == "fixture":
            body["fixture_label"] = "local-sarvam-fixtures"
        return JSONResponse(body)

    @app.get("/v1/capabilities")
    def capabilities() -> dict[str, str]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": app.state.mode,
            "port": PORT,
        }

    def _unauthorized(request_id: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "code": "UNAUTHORIZED",
                "message": "Valid bearer token required",
                "request_id": request_id,
            },
        )

    def _error(status: int, code: str, message: str, request_id: str) -> JSONResponse:
        safe = redact_secrets(message)
        if contains_secret(safe):
            safe = "Redacted error"
        logger.info("voice_error code=%s request_id=%s", code, request_id)
        return JSONResponse(
            status_code=status,
            content={"code": code, "message": safe, "request_id": request_id},
        )

    @app.post("/v1/transcribe")
    async def transcribe_route(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal = app.state.tokens.resolve(request.headers.get("authorization"))
        if principal is None:
            return _unauthorized(request_id)
        try:
            body: Any = await request.json()
        except Exception:
            return _error(422, "INVALID_INPUT", "Body must be JSON", request_id)
        try:
            voice_request = parse_voice_request(body)
            result = app.state.transcribe(principal, voice_request, request_id=request_id)
        except VoiceConsentError as exc:
            return _error(403, exc.code, exc.message, request_id)
        except VoiceForbiddenError as exc:
            return _error(403, exc.code, exc.message, request_id)
        except VoiceInputError as exc:
            return _error(422, exc.code, exc.message, request_id)
        except VoiceProviderError as exc:
            # Text fallback is a client choice; surface provider failure explicitly.
            payload = {
                "code": exc.code,
                "message": redact_secrets(exc.message),
                "request_id": request_id,
                "reason_codes": [exc.code, rc.TEXT_FALLBACK_AVAILABLE, rc.NO_FINANCIAL_AUTHORITY],
            }
            return JSONResponse(status_code=exc.status_code, content=payload)
        return JSONResponse(status_code=200, content=result.as_dict())

    @app.post("/v1/speak")
    async def speak_route(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        principal = app.state.tokens.resolve(request.headers.get("authorization"))
        if principal is None:
            return _unauthorized(request_id)
        try:
            body: Any = await request.json()
        except Exception:
            return _error(422, "INVALID_INPUT", "Body must be JSON", request_id)
        try:
            speak_request = parse_speak_request(body)
            result = app.state.speak(principal, speak_request)
        except VoiceConsentError as exc:
            return _error(403, exc.code, exc.message, request_id)
        except VoiceForbiddenError as exc:
            return _error(403, exc.code, exc.message, request_id)
        except VoiceInputError as exc:
            return _error(422, exc.code, exc.message, request_id)
        except VoiceProviderError as exc:
            return _error(exc.status_code, exc.code, exc.message, request_id)
        return JSONResponse(status_code=200, content=result.as_dict())

    return app

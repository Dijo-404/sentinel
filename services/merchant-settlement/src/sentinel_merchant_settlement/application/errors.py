"""Application-boundary errors mapped to HTTP by adapters."""

from __future__ import annotations


class SettlementError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(SettlementError):
    code = "UNAUTHORIZED"
    http_status = 401


class ForbiddenError(SettlementError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(SettlementError):
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(SettlementError):
    code = "IDEMPOTENCY_CONFLICT"
    http_status = 409


class ValidationError(SettlementError):
    code = "INVALID_INPUT"
    http_status = 422


class PeerUnavailableError(SettlementError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class PeerUnauthorizedError(SettlementError):
    code = "PEER_UNAUTHORIZED"
    http_status = 403


class PeerMalformedError(SettlementError):
    code = "PEER_MALFORMED"
    http_status = 502


class ConfigurationError(SettlementError):
    code = "CONFIGURATION"
    http_status = 500

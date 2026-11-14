"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class OpsActivityError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(OpsActivityError):
    code = "FORBIDDEN"
    http_status = 403


class ValidationError(OpsActivityError):
    code = "INVALID_INPUT"
    http_status = 422


class PeerUnavailableError(OpsActivityError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class ConfigurationError(OpsActivityError):
    code = "CONFIGURATION"
    http_status = 500

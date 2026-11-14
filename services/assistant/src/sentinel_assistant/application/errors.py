"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class AssistantError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(AssistantError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(AssistantError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(AssistantError):
    code = "INVALID_INPUT"
    http_status = 422


class PeerUnavailableError(AssistantError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class ConfigurationError(AssistantError):
    code = "CONFIGURATION"
    http_status = 500

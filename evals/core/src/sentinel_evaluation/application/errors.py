"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class EvaluationError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(EvaluationError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(EvaluationError):
    code = "NOT_FOUND"
    http_status = 404


class PeerUnavailableError(EvaluationError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class ConfigurationError(EvaluationError):
    code = "CONFIGURATION"
    http_status = 500

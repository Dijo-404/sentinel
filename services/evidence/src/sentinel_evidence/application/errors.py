"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class EvidenceError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(EvidenceError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(EvidenceError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(EvidenceError):
    code = "INVALID_INPUT"
    http_status = 422


class PeerUnavailableError(EvidenceError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class PeerUnauthorizedError(EvidenceError):
    code = "PEER_UNAUTHORIZED"
    http_status = 403


class PeerMalformedError(EvidenceError):
    code = "PEER_MALFORMED"
    http_status = 502


class ConfigurationError(EvidenceError):
    code = "CONFIGURATION"
    http_status = 500

"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class DisputeError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(DisputeError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(DisputeError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(DisputeError):
    code = "INVALID_INPUT"
    http_status = 422


class ConflictError(DisputeError):
    code = "CONFLICT"
    http_status = 409


class MissingEvidenceError(DisputeError):
    code = "MISSING_REQUIRED_EVIDENCE"
    http_status = 422

    def __init__(self, missing: tuple[str, ...], *, request_id: str = "request-local"):
        kinds = ", ".join(missing)
        super().__init__(f"Missing required evidence kinds: {kinds}", request_id=request_id)
        self.missing = missing


class DeadlinePassedError(DisputeError):
    code = "DEADLINE_PASSED"
    http_status = 422


class PeerUnavailableError(DisputeError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class PeerUnauthorizedError(DisputeError):
    code = "PEER_UNAUTHORIZED"
    http_status = 403


class PeerMalformedError(DisputeError):
    code = "PEER_MALFORMED"
    http_status = 502


class ConfigurationError(DisputeError):
    code = "CONFIGURATION"
    http_status = 500

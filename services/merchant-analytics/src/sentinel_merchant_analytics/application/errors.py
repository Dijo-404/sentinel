"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class AnalyticsError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(AnalyticsError):
    code = "FORBIDDEN"
    http_status = 403


class ValidationError(AnalyticsError):
    code = "INVALID_INPUT"
    http_status = 422


class PeerUnavailableError(AnalyticsError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class PeerUnauthorizedError(AnalyticsError):
    code = "PEER_UNAUTHORIZED"
    http_status = 403


class PeerMalformedError(AnalyticsError):
    code = "PEER_MALFORMED"
    http_status = 502


class ConfigurationError(AnalyticsError):
    code = "CONFIGURATION"
    http_status = 500

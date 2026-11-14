"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class KnowledgeError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(KnowledgeError):
    code = "FORBIDDEN"
    http_status = 403


class ValidationError(KnowledgeError):
    code = "INVALID_INPUT"
    http_status = 422


class NotFoundError(KnowledgeError):
    code = "ARTICLE_NOT_FOUND"
    http_status = 404


class PeerUnavailableError(KnowledgeError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class ConfigurationError(KnowledgeError):
    code = "CONFIGURATION"
    http_status = 500

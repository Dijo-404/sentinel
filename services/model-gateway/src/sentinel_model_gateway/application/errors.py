"""Gateway errors mapped to HTTP status at the boundary."""

from __future__ import annotations


class GatewayError(Exception):
    code = "GATEWAY_ERROR"
    http_status = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(GatewayError):
    code = "CONFIGURATION_ERROR"


class UnauthorizedError(GatewayError):
    code = "UNAUTHORIZED"
    http_status = 401


class UpstreamUnavailableError(GatewayError):
    """Sarvam or knowledge unreachable/failing. 503 so callers treat it as a retryable outage."""

    code = "UPSTREAM_UNAVAILABLE"
    http_status = 503


class ModelOutputInvalidError(GatewayError):
    """LLM output stayed invalid after one retry (replies only; proposals escalate instead)."""

    code = "MODEL_OUTPUT_INVALID"
    http_status = 502

"""Domain and application failure kinds mapped to HTTP at the adapter edge."""


class VerifierError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ConflictError(VerifierError):
    def __init__(self, message: str, *, code: str = "CONFLICT") -> None:
        super().__init__(code, message, http_status=409)


class ForbiddenError(VerifierError):
    def __init__(self, message: str = "Unauthorized scope") -> None:
        super().__init__("FORBIDDEN", message, http_status=403)


class NotFoundError(VerifierError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__("NOT_FOUND", message, http_status=404)


class ValidationError(VerifierError):
    def __init__(self, message: str, *, code: str = "INVALID_INPUT") -> None:
        super().__init__(code, message, http_status=422)


class PeerUnavailableError(VerifierError):
    def __init__(self, message: str = "Required peer unavailable") -> None:
        super().__init__("PEER_UNAVAILABLE", message, http_status=503)


class UnauthorizedError(VerifierError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("UNAUTHORIZED", message, http_status=401)


class PeerError(VerifierError):
    def __init__(self, code: str, message: str, *, status_code: int = 502) -> None:
        super().__init__(code, message, http_status=status_code)

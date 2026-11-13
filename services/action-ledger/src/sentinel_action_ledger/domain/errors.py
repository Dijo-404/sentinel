"""Domain and application failure kinds mapped to HTTP at the adapter edge."""


class LedgerError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ConflictError(LedgerError):
    def __init__(self, message: str, *, code: str = "CONFLICT") -> None:
        super().__init__(code, message, http_status=409)


class ForbiddenError(LedgerError):
    def __init__(self, message: str = "Unauthorized scope") -> None:
        super().__init__("FORBIDDEN", message, http_status=403)


class NotFoundError(LedgerError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__("NOT_FOUND", message, http_status=404)


class ValidationError(LedgerError):
    def __init__(self, message: str, *, code: str = "INVALID_INPUT") -> None:
        super().__init__(code, message, http_status=422)


class PeerUnavailableError(LedgerError):
    def __init__(self, message: str = "Required peer unavailable") -> None:
        super().__init__("PEER_UNAVAILABLE", message, http_status=503)


class UnauthorizedError(LedgerError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("UNAUTHORIZED", message, http_status=401)

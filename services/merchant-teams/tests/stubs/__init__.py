"""Local case-api.v1 doubles for SN-034 standalone checks."""

from .case_api import StubCaseApi
from .malformed import PROVIDER as MALFORMED
from .unauthorized_or_out_of_scope import PROVIDER as UNAUTHORIZED
from .unavailable import PROVIDER as UNAVAILABLE
from .valid import PROVIDER as VALID

__all__ = [
    "StubCaseApi",
    "VALID",
    "UNAVAILABLE",
    "MALFORMED",
    "UNAUTHORIZED",
]

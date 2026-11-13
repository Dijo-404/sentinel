"""Local peer doubles for case-api.v1 and evidence.v1."""

from .case_api import malformed as case_api_malformed
from .case_api import unauthorized_or_out_of_scope as case_api_unauthorized
from .case_api import unavailable as case_api_unavailable
from .case_api import valid as case_api_valid
from .evidence import malformed as evidence_malformed
from .evidence import unauthorized_or_out_of_scope as evidence_unauthorized
from .evidence import unavailable as evidence_unavailable
from .evidence import valid as evidence_valid

__all__ = [
    "case_api_valid",
    "case_api_unavailable",
    "case_api_malformed",
    "case_api_unauthorized",
    "evidence_valid",
    "evidence_unavailable",
    "evidence_malformed",
    "evidence_unauthorized",
]

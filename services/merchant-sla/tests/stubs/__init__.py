"""case-api.v1 peer stubs required by SN-031."""

from sentinel_merchant_sla.adapters.case_api_fixture import FixtureCaseApi


def valid():
    return FixtureCaseApi(behavior="valid")


def unavailable():
    return FixtureCaseApi(behavior="unavailable")


def malformed():
    return FixtureCaseApi(behavior="malformed")


def unauthorized_or_out_of_scope():
    return FixtureCaseApi(behavior="unauthorized_or_out_of_scope")


# Named cases for discovery / checklist parity.
PROVIDER_CASES = {
    "valid": valid,
    "unavailable": unavailable,
    "malformed": malformed,
    "unauthorized_or_out_of_scope": unauthorized_or_out_of_scope,
}

__all__ = [
    "PROVIDER_CASES",
    "malformed",
    "unauthorized_or_out_of_scope",
    "unavailable",
    "valid",
]

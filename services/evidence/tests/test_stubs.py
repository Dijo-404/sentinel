"""Required local peer doubles are importable and explicit."""

import pytest

from sentinel_evidence.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_evidence.domain.types import Principal
from tests.stubs import (
    CONFLICTING,
    EQUAL_ONLY,
    MALFORMED,
    STALE,
    UNAUTHORIZED,
    UNAVAILABLE,
    VALID,
    malformed,
    unauthorized_or_out_of_scope,
    unavailable,
    valid,
)
from tests.stubs.malformed import PROVIDER as MALFORMED_PROVIDER
from tests.stubs.unauthorized_or_out_of_scope import PROVIDER as UNAUTH_PROVIDER
from tests.stubs.unavailable import PROVIDER as UNAVAILABLE_PROVIDER
from tests.stubs.valid import PROVIDER as VALID_PROVIDER

PRINCIPAL = Principal("svc", "tenant-demo", ("workflow",), ("subj-demo-1",), ("case-demo-42",))


def test_stub_modules_exist():
    assert valid.PROVIDER is VALID_PROVIDER
    assert unavailable.PROVIDER is UNAVAILABLE_PROVIDER
    assert malformed.PROVIDER is MALFORMED_PROVIDER
    assert unauthorized_or_out_of_scope.PROVIDER is UNAUTH_PROVIDER
    assert {VALID, STALE, CONFLICTING, EQUAL_ONLY, UNAVAILABLE, MALFORMED, UNAUTHORIZED}


def test_stub_cases_raise_explicitly():
    with pytest.raises(PeerUnavailableError):
        UNAVAILABLE_PROVIDER.fetch_snapshot(order_reference="x", principal=PRINCIPAL)
    with pytest.raises(PeerMalformedError):
        MALFORMED_PROVIDER.fetch_snapshot(order_reference="x", principal=PRINCIPAL)
    with pytest.raises(PeerUnauthorizedError):
        UNAUTH_PROVIDER.fetch_snapshot(order_reference="x", principal=PRINCIPAL)

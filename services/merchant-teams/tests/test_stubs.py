"""Local case-api stub cases required by SN-034."""

from __future__ import annotations

import pytest
from tests.conftest import OPERATOR
from tests.stubs import MALFORMED, UNAUTHORIZED, UNAVAILABLE, VALID

from sentinel_merchant_teams.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)


def test_valid_stub_returns_case():
    snap = VALID.get_case("case-demo-42", principal=OPERATOR)
    assert snap.case_id == "case-demo-42"
    assert snap.revision == 1


def test_unavailable_stub():
    with pytest.raises(PeerUnavailableError):
        UNAVAILABLE.get_case("case-demo-42", principal=OPERATOR)


def test_malformed_stub():
    with pytest.raises(PeerMalformedError):
        MALFORMED.get_case("case-demo-42", principal=OPERATOR)


def test_unauthorized_stub():
    with pytest.raises(PeerUnauthorizedError):
        UNAUTHORIZED.get_case("case-demo-42", principal=OPERATOR)

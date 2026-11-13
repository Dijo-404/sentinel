"""Stub catalogue covers required peer failure cases without sibling imports."""

from __future__ import annotations

import pytest

from sentinel_merchant_comms.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.types import Principal
from tests.stubs import (
    MalformedCaseApi,
    MalformedIndicContext,
    UnauthorizedCaseApi,
    UnauthorizedIndicContext,
    UnavailableCaseApi,
    UnavailableIndicContext,
    ValidCaseApi,
    ValidIndicContext,
)


@pytest.fixture
def principal() -> Principal:
    return Principal(
        principal_id="op-demo",
        tenant_id="tenant-demo",
        roles=["operator"],
        subject_refs=["subject-demo"],
        case_ids=["case-demo-42"],
    )


def test_case_api_stub_cases(principal) -> None:
    case = ValidCaseApi().get_case("case-demo-42", principal)
    assert case.case_id == "case-demo-42"

    with pytest.raises(PeerUnavailableError):
        UnavailableCaseApi().get_case("case-demo-42", principal)
    with pytest.raises(PeerMalformedError):
        MalformedCaseApi().get_case("case-demo-42", principal)
    with pytest.raises(PeerUnauthorizedError):
        UnauthorizedCaseApi().get_case("case-demo-42", principal)


def test_indic_stub_cases(principal) -> None:
    case = ValidCaseApi().get_case("case-demo-42", principal)
    ok = ValidIndicContext().draft_status(case=case, language="en", principal=principal)
    assert "case-demo-42" in ok.body
    assert ok.evidence_mode == "fake-inference"

    with pytest.raises(PeerUnavailableError):
        UnavailableIndicContext().draft_status(case=case, language="en", principal=principal)
    with pytest.raises(PeerMalformedError):
        MalformedIndicContext().draft_status(case=case, language="en", principal=principal)
    with pytest.raises(PeerUnauthorizedError):
        UnauthorizedIndicContext().draft_status(case=case, language="en", principal=principal)

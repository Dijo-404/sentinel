import pytest

from sentinel_workflow.application.errors import PeerError, PeerUnavailableError
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy, StubVerifier


@pytest.mark.parametrize(
    "stub_cls",
    [StubCaseApi, StubEvidence, StubPolicy, StubLedger, StubVerifier],
)
def test_unavailable_and_unauthorized(stub_cls):
    with pytest.raises(PeerUnavailableError):
        _touch(stub_cls(behavior="unavailable"))
    with pytest.raises(PeerError) as exc:
        _touch(stub_cls(behavior="unauthorized_or_out_of_scope"))
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "stub_cls",
    [StubCaseApi, StubEvidence, StubPolicy, StubLedger, StubVerifier],
)
def test_malformed(stub_cls):
    with pytest.raises(PeerError) as exc:
        _touch(stub_cls(behavior="malformed"))
    assert exc.value.code == "MALFORMED"


def _touch(stub):
    if isinstance(stub, StubCaseApi):
        return stub.get_case("case-demo-42")
    if isinstance(stub, StubEvidence):
        return stub.collect("case-demo-42", 1, "DEMO-ORDER-42")
    if isinstance(stub, StubPolicy):
        from sentinel_workflow.domain.types import PolicyRequest

        return stub.evaluate(PolicyRequest(payload={"action": "ESCALATE"}, evidence=[]))
    if isinstance(stub, StubLedger):
        from sentinel_workflow.domain.types import ProposalRequest, RefundAction

        return stub.create_proposal(
            ProposalRequest(
                operation_key="k",
                payload=RefundAction(
                    case_id="case-demo-42",
                    case_revision=1,
                    transaction_ref="TXN-B",
                    amount_minor=1,
                    evidence_ids=["e1"],
                    policy_version="demo-policy-v1",
                ),
                action_digest="d",
            )
        )
    if isinstance(stub, StubVerifier):
        from sentinel_workflow.domain.types import VerificationRequest

        return stub.assess(
            VerificationRequest(
                case_id="case-demo-42",
                case_revision=1,
                action_id="a1",
                provider_ref="p1",
            )
        )
    raise AssertionError(type(stub))

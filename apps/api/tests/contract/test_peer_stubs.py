"""Peer stub matrix: valid / unavailable / malformed / unauthorized."""

import pytest

from sentinel_api.adapters.peers.errors import PeerError
from sentinel_api.domain.types import DecisionRequest, WorkflowRequest
from tests.stubs import action_ledger, evidence, verifier, workflow


@pytest.mark.parametrize("port", [workflow, evidence, action_ledger, verifier])
@pytest.mark.parametrize(
    "behavior",
    ["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_stub_behaviors(port, behavior):
    assert behavior in port.CASES
    client = port.make(behavior)
    if port is workflow:
        req = WorkflowRequest(case_id="c1", case_revision=1, job_key="j1", event="START")
        if behavior == "valid":
            client.start_run(req, authorization="Bearer t")
            assert client.calls
        else:
            with pytest.raises(PeerError):
                client.start_run(req, authorization="Bearer t")
    elif port is evidence:
        if behavior == "valid":
            bundle = client.get_case_evidence("c1", authorization="Bearer t")
            assert bundle.case_id == "c1"
        else:
            with pytest.raises(PeerError):
                client.get_case_evidence("c1", authorization="Bearer t")
    elif port is action_ledger:
        req = DecisionRequest(
            decision="APPROVE",
            action_digest="d",
            case_revision=1,
            policy_version="p",
            expires_at="2099-01-01T00:00:00Z",
        )
        if behavior == "valid":
            approval = client.decide("a1", req, authorization="Bearer supervisor")
            assert approval.reviewer_id == "supervisor"
            assert approval.action_digest == "d"
            assert client.last_authorization == "Bearer supervisor"
        else:
            with pytest.raises(PeerError):
                client.decide("a1", req, authorization="Bearer supervisor")
    else:
        if behavior == "valid":
            with pytest.raises(PeerError):
                # valid stub still requires a seeded assessment
                client.get_assessment("missing", authorization="Bearer t")
        else:
            with pytest.raises(PeerError):
                client.get_assessment("a1", authorization="Bearer t")

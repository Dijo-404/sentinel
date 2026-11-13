from __future__ import annotations

import pytest
from stubs import (
    MalformedActionLedger,
    MalformedEvidence,
    MalformedFinHarnessSdk,
    MalformedIndicContext,
    MalformedPolicy,
    MalformedVerifier,
    UnauthorizedActionLedger,
    UnauthorizedEvidence,
    UnauthorizedFinHarnessSdk,
    UnauthorizedIndicContext,
    UnauthorizedPolicy,
    UnauthorizedVerifier,
    UnavailableActionLedger,
    UnavailableEvidence,
    UnavailableFinHarnessSdk,
    UnavailableIndicContext,
    UnavailablePolicy,
    UnavailableVerifier,
    ValidActionLedger,
    ValidEvidence,
    ValidFinHarnessSdk,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)

from sentinel_finharness_runtime.domain.errors import PeerError


def test_valid_stubs_return_fixture_shapes():
    assert ValidEvidence().collect({"case_id": "c", "case_revision": 1, "order_reference": "o"})[
        "contract_version"
    ]
    assert ValidPolicy().evaluate({"payload": {}, "evidence": []})["outcome"] == "REQUIRE_APPROVAL"
    assert (
        ValidIndicContext().propose(
            {
                "case": {},
                "input": {"original_text": "t", "language": "en-IN"},
                "evidence": [],
            }
        )["outcome"]
        == "PROPOSAL"
    )
    assert ValidActionLedger().query_by_provider_ref("refund-demo-1")["provider_ref"] == (
        "refund-demo-1"
    )
    assert (
        ValidVerifier().assess(
            {"case_id": "c", "case_revision": 1, "action_id": "a", "provider_ref": "r"}
        )["status"]
        == "WAITING"
    )
    assert ValidFinHarnessSdk().run_read_path({})["proposal"]["action"] == "REQUEST_REFUND"


@pytest.mark.parametrize(
    ("stub", "call"),
    [
        (UnavailableEvidence(), lambda s: s.collect({})),
        (UnavailablePolicy(), lambda s: s.evaluate({})),
        (UnavailableIndicContext(), lambda s: s.propose({})),
        (UnavailableActionLedger(), lambda s: s.get_action("a")),
        (UnavailableVerifier(), lambda s: s.assess({})),
        (UnavailableFinHarnessSdk(), lambda s: s.run_read_path({})),
        (UnauthorizedEvidence(), lambda s: s.collect({})),
        (UnauthorizedPolicy(), lambda s: s.evaluate({})),
        (UnauthorizedIndicContext(), lambda s: s.propose({})),
        (UnauthorizedActionLedger(), lambda s: s.get_action("a")),
        (UnauthorizedVerifier(), lambda s: s.assess({})),
        (UnauthorizedFinHarnessSdk(), lambda s: s.run_read_path({})),
    ],
)
def test_unavailable_and_unauthorized_stubs_raise(stub, call):
    with pytest.raises(PeerError) as exc:
        call(stub)
    assert exc.value.code in {"unavailable", "unauthorized_or_out_of_scope"}


def test_malformed_stubs_return_incomplete_payloads():
    assert not isinstance(MalformedEvidence().collect({}).get("evidence"), list)
    assert MalformedPolicy().evaluate({}).get("outcome") == "MAYBE"
    assert "proposal" not in MalformedIndicContext().propose({})
    assert "provider_ref" not in MalformedActionLedger().get_action("a")
    assert "case_id" not in MalformedVerifier().assess({})
    assert "proposal" not in MalformedFinHarnessSdk().run_read_path({})

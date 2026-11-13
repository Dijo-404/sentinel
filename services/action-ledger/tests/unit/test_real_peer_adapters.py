"""Real-peer adapters fail closed; no silent fixture fallback."""

import pytest

from sentinel_action_ledger.adapters.evidence_client import HttpEvidenceClient
from sentinel_action_ledger.adapters.policy_client import HttpPolicyClient
from sentinel_action_ledger.domain.errors import PeerUnavailableError


def test_policy_client_requires_base_url():
    with pytest.raises(PeerUnavailableError):
        HttpPolicyClient("", token="x")


def test_evidence_client_requires_base_url():
    with pytest.raises(PeerUnavailableError):
        HttpEvidenceClient("", token="x")

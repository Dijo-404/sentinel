from __future__ import annotations

import pytest

from sentinel_finharness_runtime.adapters.composition import default_shadow_config, real_peer_ports
from sentinel_finharness_runtime.adapters.real_peers import (
    RealEvidenceAdapter,
    RealLedgerAdapter,
    RealPeerConfig,
    RealSdkAdapter,
)
from sentinel_finharness_runtime.adapters.store import MemoryCaseStore
from sentinel_finharness_runtime.application.runtime import FinHarnessRuntime
from sentinel_finharness_runtime.domain.errors import PeerError


def test_real_peer_config_absent_by_default():
    cfg = RealPeerConfig()
    assert cfg.any_configured is False


def test_real_evidence_fails_closed_when_url_absent():
    adapter = RealEvidenceAdapter(None)
    with pytest.raises(PeerError) as exc:
        adapter.collect({"case_id": "c", "case_revision": 1, "order_reference": "o"})
    assert exc.value.peer == "evidence.v1"
    assert exc.value.code == "unavailable"


def test_real_sdk_fails_closed_when_url_absent():
    adapter = RealSdkAdapter(None)
    with pytest.raises(PeerError) as exc:
        adapter.run_read_path({})
    assert exc.value.peer == "finharness-sdk.v1"
    assert exc.value.code == "unavailable"


def test_real_ledger_fails_closed_when_url_absent():
    adapter = RealLedgerAdapter(None)
    with pytest.raises(PeerError) as exc:
        adapter.query_by_provider_ref("refund-demo-1")
    assert exc.value.peer == "action-ledger.v1"
    assert exc.value.code == "unavailable"


def test_real_peer_runtime_does_not_fixture_fallback(manifest):
    ports = real_peer_ports(RealPeerConfig(), store=MemoryCaseStore())
    runtime = FinHarnessRuntime(config=default_shadow_config(), ports=ports)
    runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    with pytest.raises(PeerError) as exc:
        runtime.run_shadow(
            case_id="case-demo-42",
            baseline_proposal={"action": "REQUEST_REFUND", "amount_minor": 1},
        )
    assert exc.value.code == "unavailable"
    assert "fixture" not in str(exc.value).lower()

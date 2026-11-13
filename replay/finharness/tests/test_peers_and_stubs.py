from __future__ import annotations

import pytest
from stubs.finbench.stub import FinbenchStub
from stubs.finbench.stub import load_case as load_finbench
from stubs.finharness_runtime.stub import RuntimeStub
from stubs.finharness_runtime.stub import load_case as load_runtime
from stubs.replay.stub import ReplayStub
from stubs.replay.stub import load_case as load_replay

from sentinel_harness_replay.adapters.real_peers import (
    PeerUnavailable,
    RealFinbenchAdapter,
    RealPeerConfig,
    RealReplayAdapter,
    RealRuntimeAdapter,
)
from sentinel_harness_replay.application.service import compare_candidates, default_deps


def test_runtime_stub_cases() -> None:
    assert RuntimeStub("valid").capabilities()["mode"] == "fixture"
    with pytest.raises(RuntimeError):
        RuntimeStub("unavailable").capabilities()
    malformed = RuntimeStub("malformed").capabilities()
    assert malformed["mode"] == "mystery"
    with pytest.raises(PermissionError):
        RuntimeStub("unauthorized_or_out_of_scope").capabilities()
    assert load_runtime("valid")["shadow_response"]["status"] == "PASS"


def test_finbench_stub_cases() -> None:
    assert FinbenchStub("valid").score_candidate({})["status"] == "PASS"
    with pytest.raises(RuntimeError):
        FinbenchStub("unavailable").score_candidate({})
    bad = FinbenchStub("malformed").score_candidate({})
    assert bad["status"] == "YES"
    with pytest.raises(PermissionError):
        FinbenchStub("unauthorized_or_out_of_scope").score_candidate({})
    assert load_finbench("valid")["capabilities"]["component"] == "finbench"


def test_replay_stub_cases() -> None:
    assert ReplayStub("valid").compare({})["status"] == "PASS"
    with pytest.raises(RuntimeError):
        ReplayStub("unavailable").compare({})
    bad = ReplayStub("malformed").compare({})
    assert bad["status"] == "YES"
    with pytest.raises(PermissionError):
        ReplayStub("unauthorized_or_out_of_scope").compare({})
    assert load_replay("valid")["capabilities"]["component"] == "replay"


def test_real_adapters_fail_closed_when_absent() -> None:
    with pytest.raises(PeerUnavailable) as runtime_exc:
        RealRuntimeAdapter(None).shadow_compare({})
    assert runtime_exc.value.payload["code"] == "PEER_UNAVAILABLE"
    with pytest.raises(PeerUnavailable) as finbench_exc:
        RealFinbenchAdapter(None).score_candidate({})
    assert finbench_exc.value.payload["code"] == "PEER_UNAVAILABLE"
    with pytest.raises(PeerUnavailable) as replay_exc:
        RealReplayAdapter(None).compare({})
    assert replay_exc.value.payload["code"] == "PEER_UNAVAILABLE"


def test_real_peers_mode_without_urls_fails_explicitly() -> None:
    report = compare_candidates(
        run_id="real-peers-missing",
        mode="real-peers",
        deps=default_deps(peer_config=RealPeerConfig()),
    )
    assert report.status == "FAIL"
    assert report.modes.real_runtime_adapter == "absent"
    assert report.modes.real_finbench_adapter == "absent"
    assert report.modes.real_replay_adapter == "absent"
    assert any(c.reason_code == "PEER_UNAVAILABLE" for c in report.checks)
    assert all(a.evidence_mode != "real-component" for a in report.output_artifacts)


def test_fixture_run_never_claims_product_evidence() -> None:
    report = compare_candidates(mode="fixture")
    assert report.output_artifacts[0].evidence_mode == "fixture"
    assert report.modes.model_mode == "fake"

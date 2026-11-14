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


def test_real_peers_configured_urls_exercise_capabilities(monkeypatch) -> None:
    import json

    class _Resp:
        status = 200

        def __init__(self, body: dict) -> None:
            self._body = json.dumps(body).encode("utf-8")

        def read(self) -> bytes:
            return self._body

        def getcode(self) -> int:
            return 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def opener(request, timeout=5.0):  # noqa: ARG001
        url = request.full_url
        if url.endswith("/healthz"):
            return _Resp({"status": "ok"})
        if "runtime" in url and url.endswith("/v1/capabilities"):
            return _Resp(
                {
                    "contract_version": "sentinel.task-contracts.v1",
                    "component": "finharness-runtime",
                    "mode": "real-peers",
                }
            )
        if "finbench" in url and url.endswith("/v1/capabilities"):
            return _Resp(
                {
                    "contract_version": "sentinel.task-contracts.v1",
                    "component": "finbench",
                    "mode": "real-peers",
                }
            )
        if "replay" in url and url.endswith("/v1/capabilities"):
            return _Resp(
                {
                    "contract_version": "sentinel.task-contracts.v1",
                    "component": "replay",
                    "mode": "real-peers",
                }
            )
        raise AssertionError(url)

    monkeypatch.setattr(
        "sentinel_harness_replay.adapters.real_peers.urllib.request.urlopen", opener
    )
    report = compare_candidates(
        run_id="real-peers-exercised",
        mode="real-peers",
        deps=default_deps(
            peer_config=RealPeerConfig(
                runtime_url="http://runtime.example",
                finbench_url="http://finbench.example",
                replay_url="http://replay.example",
            )
        ),
    )
    assert report.status == "PASS"
    by_name = {c.name: c.reason_code for c in report.checks}
    assert by_name["real-peers.finharness-runtime"] == "PEER_CAPABILITIES_OK"
    assert by_name["real-peers.finbench"] == "PEER_CAPABILITIES_OK"
    assert by_name["real-peers.replay"] == "PEER_CAPABILITIES_OK"


def test_real_peers_configured_but_unreachable_fails(monkeypatch) -> None:
    import urllib.error

    def boom(request, timeout=5.0):  # noqa: ARG001
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("sentinel_harness_replay.adapters.real_peers.urllib.request.urlopen", boom)
    report = compare_candidates(
        run_id="real-peers-down",
        mode="real-peers",
        deps=default_deps(
            peer_config=RealPeerConfig(
                runtime_url="http://runtime.example",
                finbench_url="http://finbench.example",
                replay_url="http://replay.example",
            )
        ),
    )
    assert report.status == "FAIL"
    assert all(
        c.reason_code == "PEER_UNAVAILABLE"
        for c in report.checks
        if c.name.startswith("real-peers.")
    )


def test_fixture_run_never_claims_product_evidence() -> None:
    report = compare_candidates(mode="fixture")
    assert report.output_artifacts[0].evidence_mode == "fixture"
    assert report.modes.model_mode == "fake"

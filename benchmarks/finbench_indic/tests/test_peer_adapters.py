"""Real-peer adapters reject unavailable/malformed/unauthorized; stubs cover cases."""

from __future__ import annotations

from pathlib import Path

import pytest
from stubs import (
    MalformedIndicContext,
    MalformedRuntime,
    UnauthorizedIndicContext,
    UnauthorizedRuntime,
    UnavailableIndicContext,
    UnavailableRuntime,
    ValidIndicContext,
    ValidRuntime,
)

from sentinel_finbench.adapters.real_peer import RealContextPeer, RealRuntimePeer
from sentinel_finbench.contracts import CONTRACT_VERSION, PeerError


def test_valid_stubs_ok():
    runtime = ValidRuntime()
    caps = runtime.capabilities()
    assert caps["contract_version"] == CONTRACT_VERSION
    report = runtime.run({"run_id": "x"})
    assert report["status"] == "PASS"
    ctx = ValidIndicContext()
    result = ctx.propose(
        {"input": {"original_text": "hello", "language": "en-IN"}, "case": {}, "evidence": []}
    )
    assert result["outcome"] == "PROPOSAL"
    assert result["original_text"] == "hello"


@pytest.mark.parametrize(
    "stub, peer, code",
    [
        (UnavailableRuntime(), "finharness-runtime.v1", "unavailable"),
        (UnauthorizedRuntime(), "finharness-runtime.v1", "unauthorized_or_out_of_scope"),
        (UnavailableIndicContext(), "indic-context.v1", "unavailable"),
        (UnauthorizedIndicContext(), "indic-context.v1", "unauthorized_or_out_of_scope"),
    ],
)
def test_stub_errors(stub, peer, code):
    with pytest.raises(PeerError) as exc:
        if hasattr(stub, "run"):
            stub.run({})
        else:
            stub.propose({})
    assert exc.value.peer == peer
    assert exc.value.code == code


def test_malformed_stubs_are_detectable():
    malformed_runtime = MalformedRuntime().run({})
    assert "contract_version" not in malformed_runtime
    malformed_ctx = MalformedIndicContext().propose({})
    assert "original_text" not in malformed_ctx


def test_real_runtime_peer_cases(module_root: Path):
    stub_dir = module_root / "tests" / "stubs" / "finharness_runtime"
    ok = RealRuntimePeer(str(stub_dir / "valid.json"))
    assert ok.run({})["status"] == "PASS"

    with pytest.raises(PeerError) as exc:
        RealRuntimePeer(str(stub_dir / "unavailable.json")).run({})
    assert exc.value.code == "unavailable"

    with pytest.raises(PeerError) as exc:
        RealRuntimePeer(str(stub_dir / "malformed.json")).run({})
    assert exc.value.code == "MALFORMED"

    with pytest.raises(PeerError) as exc:
        RealRuntimePeer(str(stub_dir / "unauthorized.json")).run({})
    assert exc.value.code == "unauthorized_or_out_of_scope"

    with pytest.raises(PeerError) as exc:
        RealRuntimePeer(str(stub_dir / "missing-file.json")).run({})
    assert exc.value.code == "PEER_UNAVAILABLE"


def test_real_context_peer_cases(module_root: Path):
    stub_dir = module_root / "tests" / "stubs" / "indic_context"
    ok = RealContextPeer(str(stub_dir / "valid.json"))
    assert ok.propose({})["outcome"] == "PROPOSAL"

    with pytest.raises(PeerError) as exc:
        RealContextPeer(str(stub_dir / "unavailable.json")).propose({})
    assert exc.value.code == "unavailable"

    with pytest.raises(PeerError) as exc:
        RealContextPeer(str(stub_dir / "malformed.json")).propose({})
    assert exc.value.code == "MALFORMED"

    with pytest.raises(PeerError) as exc:
        RealContextPeer(str(stub_dir / "unauthorized.json")).propose({})
    assert exc.value.code == "unauthorized_or_out_of_scope"

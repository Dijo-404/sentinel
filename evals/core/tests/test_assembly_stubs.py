from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_evaluation.adapters.assembly import RejectingRealAssemblyPeer, StubAssemblyPeer
from sentinel_evaluation.application.evaluate import EvaluateError

STUBS = Path(__file__).resolve().parent / "stubs" / "core_assembly"


def test_stub_cases_present() -> None:
    for name in (
        "valid.json",
        "unavailable.json",
        "malformed.json",
        "unauthorized_or_out_of_scope.json",
    ):
        assert (STUBS / name).is_file()


def test_valid_stub_probe() -> None:
    probe = StubAssemblyPeer("valid", STUBS).probe()
    assert probe["status"] == "OK"
    assert probe["capabilities"]["component"] == "core-assembly"


def test_rejecting_real_peer_no_fixture_fallback() -> None:
    with pytest.raises(EvaluateError) as exc:
        RejectingRealAssemblyPeer(None).probe()
    assert exc.value.code == "PEER_UNAVAILABLE"

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_evaluation.adapters.assembly import HttpAssemblyPeer, StubAssemblyPeer
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


def test_http_assembly_no_url_no_fixture_fallback() -> None:
    with pytest.raises(EvaluateError) as exc:
        HttpAssemblyPeer(None).probe()
    assert exc.value.code == "PEER_UNAVAILABLE"


def test_http_assembly_capabilities_ok() -> None:
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
        if url.endswith("/v1/capabilities"):
            return _Resp(
                {
                    "contract_version": "sentinel.task-contracts.v1",
                    "component": "sentinel-core-assembly",
                    "mode": "real-peers",
                }
            )
        raise AssertionError(url)

    probe = HttpAssemblyPeer("http://assembly.example", opener=opener).probe()
    assert probe["status"] == "OK"
    assert probe["capabilities"]["component"] == "core-assembly"
    assert probe["capabilities"]["mode"] == "real-peers"
    assert probe["evidence_mode"] == "real-component"


def test_http_assembly_unreachable_fails_closed() -> None:
    import urllib.error

    def opener(request, timeout=5.0):  # noqa: ARG001
        raise urllib.error.URLError("down")

    with pytest.raises(EvaluateError) as exc:
        HttpAssemblyPeer("http://assembly.example", opener=opener).probe()
    assert exc.value.code == "PEER_UNAVAILABLE"

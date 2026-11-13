"""Peer stub case matrix required by SN-014."""

from __future__ import annotations

import pytest
from stubs import PEER_FACTORIES, STUB_CASES, build_stub
from stubs._base import StubError


@pytest.mark.parametrize("port", sorted(PEER_FACTORIES))
@pytest.mark.parametrize("case", STUB_CASES)
def test_stub_cases(port: str, case: str) -> None:
    stub = build_stub(port, case)
    assert stub.port == port
    if case == "valid":
        caps = stub.capabilities()
        assert caps.port == port
        assert caps.mode == "fixture"
        body = stub.ping()
        assert body["ok"] is True
        assert body["evidence_mode"] == "fixture"
        return
    if case == "malformed":
        with pytest.raises(StubError) as caps_exc:
            stub.capabilities()
        assert caps_exc.value.code == "PEER_MALFORMED"
        body = stub.ping()
        assert "ok" not in body
        assert isinstance(body.get("amount_minor"), float)
        return
    with pytest.raises(StubError) as exc:
        stub.capabilities()
    assert exc.value.code in {"PEER_UNAVAILABLE", "PEER_UNAUTHORIZED"}
    with pytest.raises(StubError):
        stub.ping()

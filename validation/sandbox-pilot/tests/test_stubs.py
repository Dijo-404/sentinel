from __future__ import annotations

import pytest
from stubs import PORT_STUBS, STUB_CASES
from stubs._base import StubError


@pytest.mark.parametrize("port", sorted(PORT_STUBS))
@pytest.mark.parametrize("case", STUB_CASES)
def test_stub_cases(port: str, case: str) -> None:
    stub = PORT_STUBS[port](case=case)
    if case == "valid":
        caps = stub.capabilities()
        assert caps.port == port
        assert caps.mode == "fixture"
        body = stub.ping()
        assert body["ok"] is True
        return
    with pytest.raises(StubError) as exc:
        stub.capabilities()
    assert exc.value.code in {
        "PEER_UNAVAILABLE",
        "PEER_UNAUTHORIZED",
        "PEER_MALFORMED",
    }

"""Shared stub behavior helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_sandbox_pilot.domain.types import CONTRACT_VERSION, Capabilities


class StubError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PeerStub:
    port: str
    case: str
    component: str

    def capabilities(self) -> Capabilities:
        if self.case == "unavailable":
            raise StubError("PEER_UNAVAILABLE", f"{self.port} unavailable")
        if self.case == "unauthorized_or_out_of_scope":
            raise StubError("PEER_UNAUTHORIZED", f"{self.port} unauthorized")
        if self.case == "malformed":
            raise StubError("PEER_MALFORMED", f"{self.port} malformed capabilities")
        return Capabilities(
            contract_version=CONTRACT_VERSION,
            component=self.component,
            mode="fixture",
            port=self.port,
        )

    def ping(self) -> dict[str, object]:
        if self.case == "unavailable":
            raise StubError("PEER_UNAVAILABLE", f"{self.port} unavailable")
        if self.case == "unauthorized_or_out_of_scope":
            raise StubError("PEER_UNAUTHORIZED", f"{self.port} unauthorized")
        if self.case == "malformed":
            return {"not": "a-valid-peer-body", "amount_minor": 12.5}
        return {
            "contract_version": CONTRACT_VERSION,
            "port": self.port,
            "ok": True,
            "evidence_mode": "fixture",
        }

"""In-process peer doubles for consumed Run* ports. Never used as release proof."""

from __future__ import annotations

from sentinel_release_mvp.contracts import (
    CONTRACT_VERSION,
    ArtifactRef,
    CheckResult,
    PeerError,
    RunInput,
    RunReport,
)

StubCase = str  # valid | unavailable | malformed | unauthorized_or_out_of_scope


class StubPeerRunner:
    def __init__(self, port: str, case: StubCase = "valid") -> None:
        self.port = port
        self.case = case

    def run(self, request: RunInput) -> RunReport:
        if self.case == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", f"{self.port} unavailable")
        if self.case == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", f"{self.port} unauthorized or out of scope")
        if self.case == "malformed":
            # Return structurally broken payload via exception at adapter boundary.
            raise PeerError("MALFORMED", f"{self.port} returned malformed payload")
        if request.contract_version != CONTRACT_VERSION:
            raise PeerError("INCOMPATIBLE_CONTRACT", "unsupported contract_version")
        return RunReport(
            contract_version=CONTRACT_VERSION,
            run_id=request.run_id,
            mode=request.mode,
            status="PASS",
            checks=(CheckResult(f"{self.port}:self", "PASS", "STUB_VALID"),),
            output_artifacts=(
                ArtifactRef(
                    kind=f"{self.port}-report",
                    uri=f"memory://stub/{self.port}",
                    sha256="a" * 64,
                    component_version="0.0.0-stub",
                    evidence_mode="fixture",
                ),
            ),
        )


def default_stubs(case: StubCase = "valid") -> dict[str, StubPeerRunner]:
    ports = (
        "core-assembly.v1",
        "evaluation.v1",
        "replay.v1",
        "telemetry.v1",
    )
    return {port: StubPeerRunner(port, case=case) for port in ports}

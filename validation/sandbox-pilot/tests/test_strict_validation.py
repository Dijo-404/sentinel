from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_sandbox_pilot.application.validation import run_validation
from sentinel_sandbox_pilot.domain.types import (
    CONTRACT_VERSION,
    REQUIRED_PEERS,
    ArtifactRef,
    Capabilities,
    RunInput,
)


@dataclass
class PartialPeers:
    missing: set[str] = field(default_factory=set)
    mode: str = "real-peers"
    contract_version: str = CONTRACT_VERSION

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        return {
            port: Capabilities(
                contract_version=self.contract_version,
                component=f"partial-{port}",
                mode=self.mode,  # type: ignore[arg-type]
                port=port,
            )
            for port in REQUIRED_PEERS
            if port not in self.missing
        }

    def run_second_workflow(self) -> dict:
        raise AssertionError("drivers must not run when peers fail")

    def run_load(self, concurrency: int) -> dict:
        raise AssertionError("drivers must not run when peers fail")

    def run_restart(self) -> dict:
        raise AssertionError("drivers must not run when peers fail")

    def run_restore(self, *, fail_restore: bool = False) -> dict:
        raise AssertionError("drivers must not run when peers fail")

    def run_kill_switch(self) -> dict:
        raise AssertionError("drivers must not run when peers fail")

    def run_rollback(self) -> dict:
        raise AssertionError("drivers must not run when peers fail")


def _real_run(**params: object) -> RunInput:
    return RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="strict-test",
        mode="real-peers",
        input_artifacts=(
            ArtifactRef(
                kind="core-assembly",
                uri="memory://real/core-assembly",
                sha256="a" * 64,
                component_version="0.1.0",
                evidence_mode="real-component",
            ),
        ),
        parameters={"component_version": "0.1.0", **params},  # type: ignore[arg-type]
    )


def test_strict_rejects_missing_peers() -> None:
    report = run_validation(
        _real_run(),
        PartialPeers(missing={"finbench.v1"}),
    )
    assert report.status == "FAIL"
    assert any(c.reason_code == "PEER_MISSING" for c in report.checks)
    assert report.external_pilot_claimed is False


def test_strict_rejects_incompatible_contract() -> None:
    report = run_validation(
        _real_run(),
        PartialPeers(contract_version="sentinel.task-contracts.v0"),
    )
    assert report.status == "FAIL"
    assert any(c.reason_code == "PEER_INCOMPATIBLE_CONTRACT" for c in report.checks)


def test_strict_rejects_fixture_peer_mode() -> None:
    report = run_validation(_real_run(), PartialPeers(mode="fixture"))
    assert report.status == "FAIL"
    assert any(c.reason_code == "PEER_FIXTURE_NOT_REAL" for c in report.checks)


def test_strict_rejects_fixture_evidence_as_real() -> None:
    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="strict-fixture-evidence",
        mode="real-peers",
        input_artifacts=(
            ArtifactRef(
                kind="core-assembly",
                uri="memory://fixture/core-assembly",
                sha256="b" * 64,
                component_version="0.1.0",
                evidence_mode="fixture",
            ),
        ),
    )
    report = run_validation(run, PartialPeers())
    assert report.status == "FAIL"
    assert any(c.reason_code == "FIXTURE_EVIDENCE_REJECTED_IN_REAL_PEERS" for c in report.checks)


def test_strict_rejects_missing_real_evidence() -> None:
    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="strict-missing-evidence",
        mode="real-peers",
    )
    report = run_validation(run, PartialPeers())
    assert report.status == "FAIL"
    assert any(c.reason_code == "MISSING_REAL_COMPONENT_EVIDENCE" for c in report.checks)


def test_absent_external_authorization_blocks_pilot_claim() -> None:
    from sentinel_sandbox_pilot.adapters.reference import ReferenceBundle

    peers = ReferenceBundle(mode="real-peers")
    report = run_validation(
        _real_run(**{"sandbox_validation.claim_external_pilot": True}),
        peers,
    )
    assert report.status == "FAIL"
    assert report.pilot_verdict == "NOT_AUTHORIZED"
    assert any(c.reason_code == "EXTERNAL_AUTHORIZATION_ABSENT" for c in report.checks)
    assert report.external_pilot_claimed is False


def test_real_peers_without_claim_keeps_pilot_not_authorized() -> None:
    from sentinel_sandbox_pilot.adapters.reference import ReferenceBundle

    peers = ReferenceBundle(mode="real-peers")
    report = run_validation(_real_run(), peers)
    assert report.pilot_verdict == "NOT_AUTHORIZED"
    assert report.external_pilot_claimed is False
    assert report.status in {"PASS", "UNVERIFIED"}

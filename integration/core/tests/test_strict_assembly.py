"""Strict real-peers mode rejects missing/incompatible peers and fixture-as-real evidence."""

from __future__ import annotations

from sentinel_core_assembly.adapters.reference import IncompatiblePeerBundle, MissingPeerBundle
from sentinel_core_assembly.application.assembly import run_assembly
from sentinel_core_assembly.domain.types import CONTRACT_VERSION, ArtifactRef, RunInput


def test_strict_rejects_missing_peers() -> None:
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="missing-peers",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="case-api",
                    uri="memory://case-api",
                    sha256="a" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
        ),
        MissingPeerBundle(missing=("verifier.v1", "dispatcher.v1")),
    )
    assert report.status == "FAIL"
    assert report.assembled_mvp_claimed is False
    reasons = {c.reason_code for c in report.checks if c.status == "FAIL"}
    assert "PEER_MISSING" in reasons
    assert not any(c.name.startswith("journey.") for c in report.checks)


def test_strict_rejects_incompatible_contract() -> None:
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="bad-contract",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="b" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
        ),
        IncompatiblePeerBundle(contract_version="sentinel.task-contracts.v0", mode="real-peers"),
    )
    assert report.status == "FAIL"
    assert "PEER_INCOMPATIBLE_CONTRACT" in {c.reason_code for c in report.checks}


def test_strict_rejects_fixture_peer_mode() -> None:
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="fixture-peers",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="c" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
        ),
        IncompatiblePeerBundle(contract_version=CONTRACT_VERSION, mode="fixture"),
    )
    assert report.status == "FAIL"
    assert "PEER_FIXTURE_NOT_REAL" in {c.reason_code for c in report.checks}


def test_strict_rejects_fixture_evidence_as_real() -> None:
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="fixture-evidence",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="harness-report",
                    uri="memory://fixture-report",
                    sha256="d" * 64,
                    component_version="0.1.0",
                    evidence_mode="fixture",
                ),
            ),
        ),
        MissingPeerBundle(),  # unused because evidence fails first
    )
    assert report.status == "FAIL"
    assert "FIXTURE_EVIDENCE_REJECTED_IN_REAL_PEERS" in {c.reason_code for c in report.checks}


def test_strict_rejects_missing_real_evidence() -> None:
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="no-evidence",
            mode="real-peers",
            input_artifacts=(),
        ),
        MissingPeerBundle(),
    )
    assert report.status == "FAIL"
    assert "MISSING_REAL_COMPONENT_EVIDENCE" in {c.reason_code for c in report.checks}

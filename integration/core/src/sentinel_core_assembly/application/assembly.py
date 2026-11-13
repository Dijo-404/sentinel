"""Assemble and run journeys; strict mode never treats fixtures as real evidence."""

from __future__ import annotations

from hashlib import sha256

from sentinel_core_assembly.domain.journeys import evaluate_journey, expectation_for
from sentinel_core_assembly.domain.types import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    JOURNEYS,
    REQUIRED_PEERS,
    ArtifactRef,
    CheckResult,
    RunInput,
    RunReport,
)

from .ports import JourneyPeers


def _digest(payload: str) -> str:
    return sha256(payload.encode("utf-8")).hexdigest()


def _rollup(checks: list[CheckResult]) -> str:
    if any(c.status == "FAIL" for c in checks):
        return "FAIL"
    if any(c.status == "UNVERIFIED" for c in checks):
        return "UNVERIFIED"
    return "PASS"


def validate_input(run: RunInput) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if run.contract_version != CONTRACT_VERSION:
        checks.append(CheckResult("contract.version", "FAIL", "CONTRACT_VERSION_MISMATCH"))
    else:
        checks.append(CheckResult("contract.version", "PASS", "CONTRACT_VERSION_OK"))
    if run.mode not in ("fixture", "real-peers"):
        checks.append(CheckResult("run.mode", "FAIL", "UNSUPPORTED_MODE"))
    else:
        checks.append(CheckResult("run.mode", "PASS", "MODE_OK"))
    for key in run.parameters:
        if not (
            key.startswith("core_assembly.")
            or key.startswith("peer.")
            or key in {"journeys", "component_version"}
        ):
            checks.append(CheckResult(f"parameter.{key}", "FAIL", "UNSUPPORTED_PARAMETER"))
    return checks


def reject_fixture_as_real(run: RunInput) -> list[CheckResult]:
    """Strict real-peers mode refuses fixture stand-ins for real component evidence."""
    checks: list[CheckResult] = []
    if run.mode != "real-peers":
        checks.append(CheckResult("evidence.policy", "PASS", "FIXTURE_MODE_ALLOWS_LOCAL_PEERS"))
        return checks
    if not run.input_artifacts:
        checks.append(CheckResult("evidence.required", "FAIL", "MISSING_REAL_COMPONENT_EVIDENCE"))
        return checks
    for artifact in run.input_artifacts:
        if artifact.evidence_mode == "fixture":
            checks.append(
                CheckResult(
                    f"evidence.{artifact.kind}",
                    "FAIL",
                    "FIXTURE_EVIDENCE_REJECTED_IN_REAL_PEERS",
                )
            )
        else:
            checks.append(
                CheckResult(
                    f"evidence.{artifact.kind}",
                    "PASS",
                    "EVIDENCE_MODE_OK",
                )
            )
    return checks


def probe_peers(peers: JourneyPeers, mode: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    try:
        caps = peers.capabilities_by_port()
    except Exception as exc:  # noqa: BLE001 — surface peer probe failures
        return [CheckResult("peers.probe", "FAIL", f"PEER_PROBE_FAILED:{type(exc).__name__}")]
    for port in REQUIRED_PEERS:
        if port not in caps:
            checks.append(CheckResult(f"peer.{port}", "FAIL", "PEER_MISSING"))
            continue
        cap = caps[port]
        if cap.contract_version != CONTRACT_VERSION:
            checks.append(CheckResult(f"peer.{port}", "FAIL", "PEER_INCOMPATIBLE_CONTRACT"))
            continue
        if mode == "real-peers" and cap.mode != "real-peers":
            checks.append(CheckResult(f"peer.{port}", "FAIL", "PEER_FIXTURE_NOT_REAL"))
            continue
        if mode == "fixture" and cap.mode not in ("fixture", "real-peers"):
            checks.append(CheckResult(f"peer.{port}", "FAIL", "PEER_MODE_UNKNOWN"))
            continue
        checks.append(CheckResult(f"peer.{port}", "PASS", "PEER_COMPATIBLE"))
    return checks


def run_journeys(peers: JourneyPeers, selected: tuple[str, ...] = JOURNEYS) -> list[CheckResult]:
    drivers = {
        "pending": peers.run_pending,
        "merchant_mismatch": peers.run_merchant_mismatch,
        "duplicate_payment": peers.run_duplicate_payment,
        "refund_pending": peers.run_refund_pending,
    }
    checks: list[CheckResult] = []
    for journey in selected:
        if journey not in drivers:
            checks.append(CheckResult(f"journey.{journey}", "FAIL", "UNKNOWN_JOURNEY"))
            continue
        try:
            outcome = drivers[journey]()
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CheckResult(f"journey.{journey}", "FAIL", f"JOURNEY_ERROR:{type(exc).__name__}")
            )
            continue
        checks.append(evaluate_journey(outcome, expectation_for(journey)))
    return checks


def run_assembly(run: RunInput, peers: JourneyPeers) -> RunReport:
    checks = validate_input(run)
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, ())

    checks.extend(reject_fixture_as_real(run))
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, ())

    checks.extend(probe_peers(peers, run.mode))
    if run.mode == "real-peers" and any(c.status == "FAIL" for c in checks):
        return _report(run, checks, ())

    selected = JOURNEYS
    raw = run.parameters.get("journeys")
    if isinstance(raw, str) and raw:
        selected = tuple(part.strip() for part in raw.split(",") if part.strip())
    checks.extend(run_journeys(peers, selected))

    # Local harness success never claims assembled MVP / product release.
    checks.append(
        CheckResult(
            "assembly.mvp_claim",
            "PASS",
            "HARNESS_PASS_IS_NOT_MVP_RELEASE",
        )
    )
    status = _rollup(checks)
    evidence_mode = "real-component" if run.mode == "real-peers" and status == "PASS" else "fixture"
    artifact = ArtifactRef(
        kind="core-assembly-report",
        uri=f"memory://core-assembly/{run.run_id}",
        sha256=_digest(f"{run.run_id}:{status}:{CONTRACT_SHA256}"),
        component_version=str(run.parameters.get("component_version", "0.1.0")),
        evidence_mode=evidence_mode,
    )
    return _report(run, checks, (artifact,), status=status)


def _report(
    run: RunInput,
    checks: list[CheckResult],
    artifacts: tuple[ArtifactRef, ...],
    status: str | None = None,
) -> RunReport:
    return RunReport(
        contract_version=CONTRACT_VERSION,
        run_id=run.run_id,
        mode=run.mode,
        status=status or _rollup(checks),  # type: ignore[arg-type]
        checks=tuple(checks),
        output_artifacts=artifacts,
        assembled_mvp_claimed=False,
    )


def report_to_exit_code(report: RunReport) -> int:
    """Self-test (fixture) exits 0 on PASS; real-peer exits nonzero on FAIL or UNVERIFIED."""
    if report.status == "PASS":
        return 0
    return 1

"""Assemble and run journeys; strict mode never treats fixtures as real evidence."""

from __future__ import annotations

import os
from hashlib import sha256

from sentinel_core_assembly.adapters.authority_path import authority_path_enabled
from sentinel_core_assembly.domain.journeys import evaluate_journey, expectation_for
from sentinel_core_assembly.domain.types import (
    AUTHORITY_FIXTURE_PATH,
    AUTHORITY_JOURNEYS,
    AUTHORITY_PATH,
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    FIXTURE_PATH,
    JOURNEYS,
    PROVIDER_JOURNEYS,
    PROVIDER_ONLY_PATH,
    REQUIRED_PEERS,
    ArtifactRef,
    CheckResult,
    RunInput,
    RunReport,
)

from .ports import JourneyPeers

# V1 sandbox assembly always labels the payment peer as simulator (not live rails).
_SANDBOX_PAYMENT_PROVIDER = "simulator"


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


def selected_journeys(run: RunInput) -> tuple[str, ...]:
    """Fixture runs provider + authority; real-peers need AUTHORITY_PATH env for SN-009."""
    raw = run.parameters.get("journeys")
    if isinstance(raw, str) and raw:
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if run.mode == "fixture":
        return JOURNEYS
    if authority_path_enabled():
        return JOURNEYS
    return PROVIDER_JOURNEYS


def run_journeys(
    peers: JourneyPeers, selected: tuple[str, ...] = JOURNEYS
) -> tuple[list[CheckResult], bool]:
    drivers = {
        "pending": peers.run_pending,
        "merchant_mismatch": peers.run_merchant_mismatch,
        "duplicate_payment": peers.run_duplicate_payment,
        "refund_pending": peers.run_refund_pending,
        "browser_to_credit": peers.run_browser_to_credit,
        "duplicate_approval_deny": peers.run_duplicate_approval_deny,
    }
    checks: list[CheckResult] = []
    sn009_exercised = False
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
        result = evaluate_journey(outcome, expectation_for(journey))
        checks.append(result)
        if (
            result.status == "PASS"
            and journey in AUTHORITY_JOURNEYS
            and bool(outcome.get("sn009_authority_exercised"))
        ):
            sn009_exercised = True
    return checks, sn009_exercised


def derive_path(mode: str, sn009_exercised: bool) -> str:
    if mode == "fixture":
        return AUTHORITY_FIXTURE_PATH if sn009_exercised else FIXTURE_PATH
    return AUTHORITY_PATH if sn009_exercised else PROVIDER_ONLY_PATH


def require_full_path_gate(run: RunInput, path: str) -> list[CheckResult]:
    """Fail closed when operator demands full MVP path but harness did not exercise it."""
    required = os.environ.get("SENTINEL_V1_REQUIRE_FULL_PATH", "").strip() == "1"
    if not required:
        return [
            CheckResult(
                "assembly.path",
                "PASS",
                "PATH_LABELED" if run.mode == "real-peers" else "FIXTURE_PATH_OK",
            )
        ]
    if path == AUTHORITY_PATH:
        return [CheckResult("assembly.path", "PASS", "FULL_PATH_SATISFIED")]
    if path == PROVIDER_ONLY_PATH:
        return [
            CheckResult(
                "assembly.path",
                "FAIL",
                "FULL_PATH_REQUIRED_BUT_PROVIDER_SANDBOX_ONLY",
            )
        ]
    return [
        CheckResult(
            "assembly.path",
            "FAIL",
            "FULL_PATH_REQUIRED_BUT_NOT_REAL_AUTHORITY",
        )
    ]


def run_assembly(run: RunInput, peers: JourneyPeers) -> RunReport:
    checks = validate_input(run)
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, (), path=derive_path(run.mode, False), sn009=False)

    checks.extend(reject_fixture_as_real(run))
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, (), path=derive_path(run.mode, False), sn009=False)

    checks.extend(probe_peers(peers, run.mode))
    if run.mode == "real-peers" and any(c.status == "FAIL" for c in checks):
        return _report(run, checks, (), path=derive_path(run.mode, False), sn009=False)

    selected = selected_journeys(run)
    journey_checks, sn009 = run_journeys(peers, selected)
    checks.extend(journey_checks)
    path = derive_path(run.mode, sn009)

    checks.extend(require_full_path_gate(run, path))

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
    return _report(run, checks, (artifact,), status=status, path=path, sn009=sn009)


def _report(
    run: RunInput,
    checks: list[CheckResult],
    artifacts: tuple[ArtifactRef, ...],
    status: str | None = None,
    path: str | None = None,
    sn009: bool = False,
) -> RunReport:
    # Fixture and real-peers both use the mock sandbox label — never live rails.
    provider = _SANDBOX_PAYMENT_PROVIDER
    report_path = path if path is not None else derive_path(run.mode, sn009)
    return RunReport(
        contract_version=CONTRACT_VERSION,
        run_id=run.run_id,
        mode=run.mode,
        status=status or _rollup(checks),  # type: ignore[arg-type]
        checks=tuple(checks),
        output_artifacts=artifacts,
        assembled_mvp_claimed=False,
        payment_provider=provider,
        path=report_path,
        sn009_authority_exercised=sn009,
    )


def report_to_exit_code(report: RunReport) -> int:
    """Self-test (fixture) exits 0 on PASS; real-peer exits nonzero on FAIL or UNVERIFIED."""
    if report.status == "PASS":
        return 0
    return 1

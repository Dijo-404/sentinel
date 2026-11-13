"""Run sandbox-validation.v1; kit PASS never claims external pilot success."""

from __future__ import annotations

from hashlib import sha256

from sentinel_sandbox_pilot.application.ports import ValidationPeers
from sentinel_sandbox_pilot.domain.drivers import evaluate_driver
from sentinel_sandbox_pilot.domain.types import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    DRIVERS,
    REQUIRED_PEERS,
    ArtifactRef,
    CheckResult,
    PilotVerdict,
    RunInput,
    RunReport,
)


def _digest(payload: str) -> str:
    return sha256(payload.encode("utf-8")).hexdigest()


def _rollup(checks: list[CheckResult]) -> str:
    if any(c.status == "FAIL" for c in checks):
        return "FAIL"
    if any(c.status == "UNVERIFIED" for c in checks):
        return "UNVERIFIED"
    return "PASS"


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


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
            key.startswith("sandbox_validation.")
            or key.startswith("peer.")
            or key in {"drivers", "component_version"}
        ):
            checks.append(CheckResult(f"parameter.{key}", "FAIL", "UNSUPPORTED_PARAMETER"))
    return checks


def reject_fixture_as_real(run: RunInput) -> list[CheckResult]:
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


def probe_peers(peers: ValidationPeers, mode: str) -> list[CheckResult]:
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


def run_drivers(
    peers: ValidationPeers, run: RunInput, selected: tuple[str, ...]
) -> list[CheckResult]:
    fail_restore = _truthy(run.parameters.get("sandbox_validation.fail_restore", False))
    concurrency_raw = run.parameters.get("sandbox_validation.load_concurrency", 8)
    concurrency = int(concurrency_raw) if isinstance(concurrency_raw, (int, str)) else 8
    drivers = {
        "second_workflow": peers.run_second_workflow,
        "load": lambda: peers.run_load(concurrency),
        "restart": peers.run_restart,
        "restore": lambda: peers.run_restore(fail_restore=fail_restore),
        "kill_switch": peers.run_kill_switch,
        "rollback": peers.run_rollback,
    }
    checks: list[CheckResult] = []
    for name in selected:
        if name not in drivers:
            checks.append(CheckResult(f"driver.{name}", "FAIL", "UNKNOWN_DRIVER"))
            continue
        try:
            outcome = drivers[name]()
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CheckResult(f"driver.{name}", "FAIL", f"DRIVER_ERROR:{type(exc).__name__}")
            )
            continue
        checks.append(evaluate_driver(name, outcome))
    return checks


def _pilot_verdict(run: RunInput, status: str) -> tuple[PilotVerdict, bool, list[CheckResult]]:
    """External pilot PASS needs separate authorization; kit success alone is KIT_ONLY."""
    checks: list[CheckResult] = []
    authorized = _truthy(run.parameters.get("sandbox_validation.external_authorization", False))
    claim_pilot = _truthy(run.parameters.get("sandbox_validation.claim_external_pilot", False))

    if run.mode == "fixture":
        checks.append(
            CheckResult(
                "pilot.external_authorization",
                "PASS",
                "FIXTURE_KIT_ONLY_NO_EXTERNAL_PILOT",
            )
        )
        if claim_pilot:
            checks.append(
                CheckResult(
                    "pilot.claim",
                    "FAIL",
                    "EXTERNAL_PILOT_CLAIM_REJECTED_IN_FIXTURE",
                )
            )
            return "NOT_AUTHORIZED", False, checks
        checks.append(CheckResult("pilot.claim", "PASS", "EXTERNAL_PILOT_NOT_CLAIMED"))
        return "KIT_ONLY", False, checks

    # real-peers: absent authorization can never yield a successful pilot verdict.
    if not authorized:
        checks.append(
            CheckResult(
                "pilot.external_authorization",
                "FAIL" if claim_pilot else "PASS",
                "EXTERNAL_AUTHORIZATION_ABSENT",
            )
        )
        if claim_pilot:
            checks.append(
                CheckResult(
                    "pilot.claim",
                    "FAIL",
                    "EXTERNAL_PILOT_CLAIM_REJECTED_WITHOUT_AUTHORIZATION",
                )
            )
        else:
            checks.append(CheckResult("pilot.claim", "PASS", "EXTERNAL_PILOT_NOT_CLAIMED"))
        return "NOT_AUTHORIZED", False, checks

    checks.append(
        CheckResult(
            "pilot.external_authorization",
            "PASS",
            "EXTERNAL_AUTHORIZATION_PRESENT",
        )
    )
    if status != "PASS":
        checks.append(CheckResult("pilot.claim", "PASS", "EXTERNAL_PILOT_NOT_CLAIMED"))
        return "FAIL" if status == "FAIL" else "UNVERIFIED", False, checks

    if claim_pilot:
        # Authorized claim still cannot auto-PASS: owner-run external evidence is separate.
        checks.append(
            CheckResult(
                "pilot.claim",
                "UNVERIFIED",
                "EXTERNAL_PILOT_AUTHORIZED_BUT_UNVERIFIED",
            )
        )
        return "UNVERIFIED", False, checks

    checks.append(CheckResult("pilot.claim", "PASS", "EXTERNAL_PILOT_NOT_CLAIMED"))
    return "KIT_ONLY", False, checks


def run_validation(run: RunInput, peers: ValidationPeers) -> RunReport:
    checks = validate_input(run)
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, "FAIL")

    checks.extend(reject_fixture_as_real(run))
    if any(c.status == "FAIL" for c in checks):
        return _report(run, checks, "FAIL")

    checks.extend(probe_peers(peers, run.mode))
    if run.mode == "real-peers" and any(c.status == "FAIL" for c in checks):
        verdict, claimed, pilot_checks = _pilot_verdict(run, "FAIL")
        checks.extend(pilot_checks)
        return _report(run, checks, "FAIL", pilot_verdict=verdict, claimed=claimed)

    selected = DRIVERS
    raw = run.parameters.get("drivers")
    if isinstance(raw, str) and raw:
        selected = tuple(part.strip() for part in raw.split(",") if part.strip())
    checks.extend(run_drivers(peers, run, selected))

    # Measured environment / unresolved limits are always labeled.
    env_label = "fixture" if run.mode == "fixture" else "real-peers"
    checks.append(
        CheckResult(
            "report.environment",
            "PASS",
            f"MEASURED_ENVIRONMENT:{env_label}",
        )
    )
    checks.append(
        CheckResult(
            "report.limits",
            "PASS" if run.mode == "fixture" else "UNVERIFIED",
            "REAL_PEER_ASSEMBLY_UNVERIFIED"
            if run.mode == "real-peers"
            else "FIXTURE_LIMITS_DOCUMENTED",
        )
    )

    status = _rollup(checks)
    verdict, claimed, pilot_checks = _pilot_verdict(run, status)
    checks.extend(pilot_checks)
    status = _rollup(checks)
    return _report(run, checks, status, pilot_verdict=verdict, claimed=claimed)


def _report(
    run: RunInput,
    checks: list[CheckResult],
    status: str,
    *,
    pilot_verdict: PilotVerdict = "KIT_ONLY",
    claimed: bool = False,
) -> RunReport:
    artifact = ArtifactRef(
        kind="sandbox-validation-report",
        uri=f"memory://sandbox-validation/{run.run_id}",
        sha256=_digest(f"{run.run_id}:{status}:{len(checks)}"),
        component_version=str(run.parameters.get("component_version", "0.1.0")),
        evidence_mode="fixture" if run.mode == "fixture" else "real-component",
    )
    return RunReport(
        contract_version=CONTRACT_VERSION,
        run_id=run.run_id,
        mode=run.mode,
        status=status,  # type: ignore[arg-type]
        checks=tuple(checks),
        output_artifacts=(artifact,),
        external_pilot_claimed=claimed,
        pilot_verdict=pilot_verdict,
    )


def self_check_report() -> RunReport:
    from sentinel_sandbox_pilot.adapters.reference import ReferenceBundle

    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="sandbox-pilot-self-check",
        mode="fixture",
        parameters={"component_version": "0.1.0"},
    )
    return run_validation(run, ReferenceBundle())


__all__ = [
    "CONTRACT_SHA256",
    "run_validation",
    "self_check_report",
]

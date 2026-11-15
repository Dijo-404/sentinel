"""Release verdict rules. Fixture-only evidence never proves a shipped product."""

from __future__ import annotations

from pathlib import Path

from sentinel_release_mvp.contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    REQUIRED_CHECK_NAMES,
    REQUIRED_PORTS,
    CheckResult,
    EvidenceManifest,
    ReleaseVerdict,
)
from sentinel_release_mvp.domain.integrity import check_component_integrity, timestamp_ok


def evaluate_manifest(
    manifest: EvidenceManifest,
    *,
    require_real_component_evidence: bool,
    artifact_root: Path | None = None,
) -> ReleaseVerdict:
    """Validate evidence and decide whether a release may be approved.

    When ``require_real_component_evidence`` is False (kit self-test / fixture mode),
    structural validation still runs, but a successful structural PASS never sets
    ``release_approved``.
    """
    checks: list[CheckResult] = []
    reasons: list[str] = []

    if manifest.contract_version != CONTRACT_VERSION:
        checks.append(CheckResult("manifest.contract_version", "FAIL", "INCOMPATIBLE_CONTRACT"))
        reasons.append("INCOMPATIBLE_CONTRACT")
    else:
        checks.append(CheckResult("manifest.contract_version", "PASS", "OK"))

    if manifest.baseline_contract_sha256 != CONTRACT_SHA256:
        checks.append(CheckResult("manifest.baseline_hash", "FAIL", "INCOMPATIBLE_BASELINE"))
        reasons.append("INCOMPATIBLE_BASELINE")
    else:
        checks.append(CheckResult("manifest.baseline_hash", "PASS", "OK"))

    if not timestamp_ok(manifest.observed_at):
        checks.append(CheckResult("manifest.observed_at", "FAIL", "INVALID_TIMESTAMP"))
        reasons.append("INVALID_TIMESTAMP")
    else:
        checks.append(CheckResult("manifest.observed_at", "PASS", "OK"))

    by_port = {c.port: c for c in manifest.components}
    for port in REQUIRED_PORTS:
        name = f"component.present:{port}"
        if port not in by_port:
            checks.append(CheckResult(name, "FAIL", "MISSING_COMPONENT"))
            reasons.append("MISSING_COMPONENT")
            continue
        checks.append(CheckResult(name, "PASS", "OK"))
        component = by_port[port]
        if component.contract_sha256 != CONTRACT_SHA256:
            checks.append(
                CheckResult(f"component.contract:{port}", "FAIL", "INCOMPATIBLE_CONTRACT")
            )
            reasons.append("INCOMPATIBLE_CONTRACT")
        else:
            checks.append(CheckResult(f"component.contract:{port}", "PASS", "OK"))
        if component.check_result != "PASS":
            checks.append(
                CheckResult(
                    f"component.check:{port}",
                    "FAIL",
                    f"CHECK_{component.check_result}",
                )
            )
            reasons.append("FAILED_COMPONENT_CHECK")
        else:
            checks.append(CheckResult(f"component.check:{port}", "PASS", "OK"))
        if require_real_component_evidence and component.evidence_mode == "fixture":
            checks.append(
                CheckResult(
                    f"component.evidence_mode:{port}",
                    "FAIL",
                    "FIXTURE_ONLY_NOT_RELEASE_PROOF",
                )
            )
            reasons.append("FIXTURE_ONLY_NOT_RELEASE_PROOF")
        elif require_real_component_evidence and component.observed_mode != "real-peers":
            checks.append(
                CheckResult(
                    f"component.observed_mode:{port}",
                    "FAIL",
                    "FIXTURE_ONLY_NOT_RELEASE_PROOF",
                )
            )
            reasons.append("FIXTURE_ONLY_NOT_RELEASE_PROOF")
        else:
            checks.append(CheckResult(f"component.evidence_mode:{port}", "PASS", "OK"))
        integrity = check_component_integrity(component, artifact_root=artifact_root)
        checks.append(integrity)
        if integrity.status != "PASS":
            reasons.append(integrity.reason_code)

    check_by_name = {c.name: c for c in manifest.required_checks}
    for req in REQUIRED_CHECK_NAMES:
        name = f"required_check:{req}"
        found = check_by_name.get(req)
        if found is None:
            checks.append(CheckResult(name, "FAIL", "MISSING_CHECK"))
            reasons.append("MISSING_CHECK")
        elif found.status != "PASS":
            checks.append(CheckResult(name, "FAIL", f"CHECK_{found.status}"))
            reasons.append("FAILED_REQUIRED_CHECK")
        else:
            checks.append(CheckResult(name, "PASS", "OK"))

    if require_real_component_evidence:
        if manifest.component_under_test != "real":
            checks.append(
                CheckResult(
                    "evidence.component_under_test",
                    "FAIL",
                    "FIXTURE_ONLY_NOT_RELEASE_PROOF",
                )
            )
            reasons.append("FIXTURE_ONLY_NOT_RELEASE_PROOF")
        else:
            checks.append(CheckResult("evidence.component_under_test", "PASS", "OK"))
        # Simulator payment + fake/live model must be labeled; neither upgrades fixture peers.
        checks.append(
            CheckResult(
                "evidence.payment_provider",
                "PASS",
                f"LABELED_{manifest.payment_provider.upper().replace('-', '_')}",
            )
        )
        checks.append(
            CheckResult(
                "evidence.model",
                "PASS",
                f"LABELED_{manifest.model.upper()}",
            )
        )

    unique_reasons = tuple(dict.fromkeys(reasons))
    if unique_reasons:
        status: str = "FAIL"
        approved = False
    elif require_real_component_evidence:
        status = "PASS"
        approved = True
    else:
        # Structural self-test OK — never claim a product release.
        status = "PASS"
        approved = False
        unique_reasons = ("SELF_TEST_NOT_RELEASE_PROOF",)

    return ReleaseVerdict(
        release_approved=approved,
        status=status,  # type: ignore[arg-type]
        reason_codes=unique_reasons,
        checks=tuple(checks),
    )

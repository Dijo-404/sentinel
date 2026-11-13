"""Verify release-evidence manifests and optional peer reports."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_release_mvp.application.ports import PeerRunner
from sentinel_release_mvp.contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    REQUIRED_PORTS,
    ArtifactRef,
    CheckResult,
    EvidenceManifest,
    PeerError,
    ReleaseVerdict,
    RunInput,
    RunReport,
)
from sentinel_release_mvp.domain.integrity import sha256_bytes
from sentinel_release_mvp.domain.verdict import evaluate_manifest


def load_manifest(path: Path) -> EvidenceManifest:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PeerError("MALFORMED", f"manifest JSON invalid: {exc}") from exc
    return EvidenceManifest.from_dict(data)


def verify_manifest(
    manifest: EvidenceManifest,
    *,
    mode: str,
    run_id: str,
    artifact_root: Path | None = None,
    peers: dict[str, PeerRunner] | None = None,
) -> tuple[RunReport, ReleaseVerdict]:
    require_real = mode == "real-peers"
    verdict = evaluate_manifest(
        manifest,
        require_real_component_evidence=require_real,
        artifact_root=artifact_root,
    )
    checks = list(verdict.checks)

    if peers is not None and require_real:
        for port in REQUIRED_PORTS:
            runner = peers.get(port)
            name = f"peer.run:{port}"
            if runner is None:
                checks.append(CheckResult(name, "FAIL", "PEER_UNAVAILABLE"))
                continue
            try:
                report = runner.run(
                    RunInput(
                        contract_version=CONTRACT_VERSION,
                        run_id=f"{run_id}:{port}",
                        mode="real-peers",
                        input_artifacts=(),
                        parameters={},
                    )
                )
            except PeerError as exc:
                checks.append(CheckResult(name, "FAIL", exc.code))
                continue
            if report.contract_version != CONTRACT_VERSION:
                checks.append(CheckResult(name, "FAIL", "INCOMPATIBLE_CONTRACT"))
            elif report.status != "PASS":
                checks.append(CheckResult(name, "FAIL", f"PEER_{report.status}"))
            else:
                checks.append(CheckResult(name, "PASS", "OK"))

    failed = [c for c in checks if c.status != "PASS"]
    if failed:
        status = "FAIL"
        approved = False
        reason_codes = tuple(dict.fromkeys(c.reason_code for c in failed))
    else:
        status = "PASS"
        approved = require_real
        reason_codes = () if require_real else ("SELF_TEST_NOT_RELEASE_PROOF",)

    final = ReleaseVerdict(
        release_approved=approved,
        status=status,  # type: ignore[arg-type]
        reason_codes=reason_codes if reason_codes else verdict.reason_codes,
        checks=tuple(checks),
    )

    payload = json.dumps(manifest.to_dict(), separators=(",", ":"), sort_keys=True).encode()
    digest = sha256_bytes(payload)
    out_art = ArtifactRef(
        kind="release-evidence-report",
        uri=f"memory://{run_id}/verdict.json",
        sha256=digest,
        component_version="0.1.0",
        evidence_mode="fixture" if not require_real else "real-component",
    )
    report = RunReport(
        contract_version=CONTRACT_VERSION,
        run_id=run_id,
        mode="real-peers" if require_real else "fixture",  # type: ignore[arg-type]
        status=final.status,
        checks=final.checks,
        output_artifacts=(out_art,),
    )
    # Attach kit metadata via unused fields? Keep RunReport pure; caller merges verdict.
    _ = PORT, CONTRACT_SHA256
    return report, final


def render_release_report(report: RunReport, verdict: ReleaseVerdict) -> str:
    lines = [
        f"# Release evidence report ({report.run_id})",
        "",
        f"- contract_version: `{report.contract_version}`",
        f"- mode: `{report.mode}`",
        f"- run_status: `{report.status}`",
        f"- release_approved: `{str(verdict.release_approved).lower()}`",
        f"- reason_codes: `{', '.join(verdict.reason_codes) or 'none'}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- [{check.status}] `{check.name}` — {check.reason_code}")
    lines.append("")
    lines.append("## Output artifacts")
    lines.append("")
    for art in report.output_artifacts:
        lines.append(
            f"- `{art.kind}` {art.uri} sha256={art.sha256} mode={art.evidence_mode}"
        )
    lines.append("")
    if not verdict.release_approved:
        lines.append(
            "Note: kit self-test PASS or blocked verdict is not product release proof."
        )
        lines.append("")
    return "\n".join(lines)

"""Wave 6 money-path verify: stub scan + fixture honesty + approval-ui smoke."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from sentinel_core_assembly.adapters.composition import build_peers
from sentinel_core_assembly.adapters.config import AssemblyConfig
from sentinel_core_assembly.adapters.portal_stub_scan import scan_portal_stubs
from sentinel_core_assembly.adapters.reference import ReferenceBundle
from sentinel_core_assembly.adapters.verify_wave4 import (
    APPROVAL_UI_EXPORT,
    APPROVAL_UI_PACKAGE_NAME,
    assert_approval_ui_package,
)
from sentinel_core_assembly.application.assembly import run_assembly
from sentinel_core_assembly.domain.types import (
    AUTHORITY_FIXTURE_PATH,
    CONTRACT_VERSION,
    ArtifactRef,
    RunInput,
)

LIVE_ENV = "VERIFY_WAVE6_LIVE"


class CheckResult(TypedDict, total=False):
    name: str
    ok: bool
    status_code: int
    detail: str


class VerifyReport(TypedDict, total=False):
    status: str
    checks: list[CheckResult]
    reason_code: str


def _repo_root() -> Path:
    # adapters → package → src → integration/core → integration → repo
    return Path(__file__).resolve().parents[5]


def assert_approval_slot_real_peers_uses_package(repo_root: Path) -> None:
    """Fail unless apps/web approval-slot mounts ApprovalPanel on real-peers."""
    slot = repo_root / "apps" / "web" / "src" / "slots" / "approval-slot.tsx"
    if not slot.is_file():
        raise AssertionError(f"missing {slot}")
    text = slot.read_text(encoding="utf-8")
    if APPROVAL_UI_EXPORT not in text:
        raise AssertionError(f"{slot} missing {APPROVAL_UI_EXPORT!r}")
    if APPROVAL_UI_PACKAGE_NAME not in text and "sentinel-approval-ui" not in text:
        raise AssertionError(f"{slot} missing import from {APPROVAL_UI_PACKAGE_NAME!r}")
    if 'mode === "real-peers"' not in text and "mode === 'real-peers'" not in text:
        raise AssertionError(f"{slot} missing real-peers mode branch")
    # Real-peers branch must appear before LocalApprovalSubstitute return path.
    panel_idx = text.find(f"<{APPROVAL_UI_EXPORT}")
    local_idx = text.find("<LocalApprovalSubstitute")
    if panel_idx < 0:
        raise AssertionError(f"{slot} does not render <{APPROVAL_UI_EXPORT}>")
    if local_idx >= 0 and panel_idx > local_idx:
        raise AssertionError(
            f"{slot} renders LocalApprovalSubstitute before {APPROVAL_UI_EXPORT} "
            "(real-peers must prefer package panel)"
        )


def assert_fixture_honesty(report) -> str:
    """Fail unless fixture assembly report carries money-path honesty labels."""
    if report.status != "PASS":
        raise AssertionError(f"fixture assembly status want PASS got {report.status!r}")
    if report.payment_provider != "simulator":
        raise AssertionError(f"payment_provider want 'simulator' got {report.payment_provider!r}")
    if report.path == "live-provider":
        raise AssertionError("path must never be live-provider")
    if report.path != AUTHORITY_FIXTURE_PATH:
        raise AssertionError(f"path want {AUTHORITY_FIXTURE_PATH!r} got {report.path!r}")
    if report.sn009_authority_exercised is not True:
        raise AssertionError("sn009_authority_exercised want true")
    if report.assembled_mvp_claimed is not False:
        raise AssertionError("assembled_mvp_claimed want false")
    return (
        f"payment_provider=simulator path={report.path} "
        "sn009_authority_exercised=true assembled_mvp_claimed=false"
    )


def _run_fixture_assembly() -> str:
    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="verify-wave6-fixture",
        mode="fixture",
        parameters={"component_version": "0.1.0"},
    )
    report = run_assembly(run, ReferenceBundle())
    return assert_fixture_honesty(report)


def _run_live_subset(env: Mapping[str, str]) -> str:
    """Provider real-peers journeys when peers are up. No live payment rails."""
    digest = "0" * 64
    artifact = ArtifactRef(
        kind="sandbox-stack",
        uri="local://v1-sandbox-wave6",
        sha256=digest,
        component_version="0.1.0",
        evidence_mode="real-component",
    )
    config = AssemblyConfig.from_env(dict(env))
    peers = build_peers(
        AssemblyConfig(
            mode="real-peers",
            contract_version=config.contract_version,
            contract_sha256=config.contract_sha256,
            peer_endpoints=config.peer_endpoints,
            tokens=config.tokens,
            tenant_id=config.tenant_id,
            case_id=config.case_id,
        )
    )
    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="verify-wave6-live",
        mode="real-peers",
        input_artifacts=(artifact,),
        parameters={"component_version": "0.1.0"},
    )
    report = run_assembly(run, peers)
    if report.status != "PASS":
        failed = [c for c in report.checks if c.status != "PASS"]
        detail = "; ".join(f"{c.name}:{c.reason_code}" for c in failed[:8])
        raise AssertionError(f"live real-peers status={report.status!r}; {detail}")
    if report.payment_provider != "simulator":
        raise AssertionError(
            f"live payment_provider want 'simulator' got {report.payment_provider!r}"
        )
    if report.path == "live-provider":
        raise AssertionError("live path must never be live-provider")
    if report.assembled_mvp_claimed is not False:
        raise AssertionError("live assembled_mvp_claimed want false")
    return (
        f"payment_provider=simulator path={report.path} "
        f"sn009_authority_exercised={str(report.sn009_authority_exercised).lower()} "
        "assembled_mvp_claimed=false"
    )


def verify_wave6(
    env: Mapping[str, str] | None = None,
    *,
    repo_root: Path | None = None,
) -> VerifyReport:
    """Portal stub scan + fixture journeys + approval-ui smoke; optional live.

    Credential-free by default. Set ``VERIFY_WAVE6_LIVE=1`` with peers up to run
    a real-peers provider subset (simulator only). Never claims MVP release.
    """
    env = env or {}
    root = repo_root or _repo_root()
    checks: list[CheckResult] = []

    web_root = root / "apps" / "web"
    try:
        scan = scan_portal_stubs(web_root)
        if scan.status != "PASS":
            hits = "; ".join(f"{h['path']}:{h['line']}:{h['text']}" for h in scan.hits[:12])
            raise AssertionError(f"stub inventory hits: {hits or '(none)'}")
        checks.append(
            {
                "name": "portal.stub_scan",
                "ok": True,
                "status_code": 0,
                "detail": "ok",
            }
        )
    except AssertionError as exc:
        checks.append(
            {
                "name": "portal.stub_scan",
                "ok": False,
                "status_code": 0,
                "detail": str(exc),
            }
        )

    try:
        detail = _run_fixture_assembly()
        checks.append(
            {
                "name": "fixture.assembly",
                "ok": True,
                "status_code": 0,
                "detail": detail,
            }
        )
    except Exception as exc:  # noqa: BLE001 — surface assembly failures as check
        checks.append(
            {
                "name": "fixture.assembly",
                "ok": False,
                "status_code": 0,
                "detail": str(exc),
            }
        )

    try:
        assert_approval_ui_package(root)
        checks.append(
            {
                "name": "approval-ui.package",
                "ok": True,
                "status_code": 0,
                "detail": "ok",
            }
        )
    except AssertionError as exc:
        checks.append(
            {
                "name": "approval-ui.package",
                "ok": False,
                "status_code": 0,
                "detail": str(exc),
            }
        )

    try:
        assert_approval_slot_real_peers_uses_package(root)
        checks.append(
            {
                "name": "approval-ui.slot",
                "ok": True,
                "status_code": 0,
                "detail": "ok",
            }
        )
    except AssertionError as exc:
        checks.append(
            {
                "name": "approval-ui.slot",
                "ok": False,
                "status_code": 0,
                "detail": str(exc),
            }
        )

    live_on = (env.get(LIVE_ENV) or "").strip() == "1"
    if not live_on:
        checks.append(
            {
                "name": "live.real_peers",
                "ok": True,
                "status_code": 0,
                "detail": (
                    "skipped: set VERIFY_WAVE6_LIVE=1 with peers up for real-peers "
                    "subset (see docs/sandbox-runbook.md); default stays credential-free"
                ),
            }
        )
    else:
        try:
            detail = _run_live_subset(env)
            checks.append(
                {
                    "name": "live.real_peers",
                    "ok": True,
                    "status_code": 0,
                    "detail": detail,
                }
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {
                    "name": "live.real_peers",
                    "ok": False,
                    "status_code": 0,
                    "detail": f"live subset failed: {exc}",
                }
            )

    if all(c.get("ok") for c in checks):
        return {"status": "PASS", "checks": checks}
    return {
        "status": "FAIL",
        "checks": checks,
        "reason_code": "WAVE6_VERIFY_FAILED",
    }

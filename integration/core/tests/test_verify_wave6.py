"""Wave 6 verify: stub scan, fixture honesty, approval-ui smoke; live optional."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sentinel_core_assembly.adapters.portal_stub_scan import StubScanReport
from sentinel_core_assembly.adapters.verify_wave4 import (
    APPROVAL_UI_EXPORT,
    APPROVAL_UI_PACKAGE_NAME,
)
from sentinel_core_assembly.adapters.verify_wave6 import (
    assert_approval_slot_real_peers_uses_package,
    verify_wave6,
)
from sentinel_core_assembly.domain.types import AUTHORITY_FIXTURE_PATH


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_verify_wave6_fails_when_stub_scan_injected(tmp_path: Path) -> None:
    fail_scan = StubScanReport(
        status="FAIL",
        hits=[{"path": "/x/page.tsx", "line": 1, "text": "Not available yet"}],
    )
    with (
        patch(
            "sentinel_core_assembly.adapters.verify_wave6.scan_portal_stubs",
            return_value=fail_scan,
        ),
        patch(
            "sentinel_core_assembly.adapters.verify_wave6.assert_approval_ui_package",
        ),
        patch(
            "sentinel_core_assembly.adapters.verify_wave6.assert_approval_slot_real_peers_uses_package",
        ),
    ):
        report = verify_wave6({}, repo_root=tmp_path)

    assert report["status"] == "FAIL"
    assert report.get("reason_code") == "WAVE6_VERIFY_FAILED"
    stub = next(c for c in report["checks"] if c["name"] == "portal.stub_scan")
    assert stub["ok"] is False
    assert "Not available yet" in stub["detail"]


def test_verify_wave6_fixture_assembly_honesty_fields() -> None:
    report = verify_wave6({})
    assert report["status"] == "PASS"
    fixture = next(c for c in report["checks"] if c["name"] == "fixture.assembly")
    assert fixture["ok"] is True
    detail = fixture["detail"]
    assert "payment_provider=simulator" in detail
    assert f"path={AUTHORITY_FIXTURE_PATH}" in detail
    assert "sn009_authority_exercised=true" in detail
    assert "assembled_mvp_claimed=false" in detail
    assert "live-provider" not in detail


def test_verify_wave6_approval_ui_import_smoke_on_repo() -> None:
    report = verify_wave6({}, repo_root=_repo_root())
    assert report["status"] == "PASS"
    pkg = next(c for c in report["checks"] if c["name"] == "approval-ui.package")
    assert pkg["ok"] is True
    slot = next(c for c in report["checks"] if c["name"] == "approval-ui.slot")
    assert slot["ok"] is True


def test_verify_wave6_skips_live_by_default() -> None:
    report = verify_wave6({})
    live = next(c for c in report["checks"] if c["name"] == "live.real_peers")
    assert live["ok"] is True
    assert "skip" in live["detail"].lower()
    assert "VERIFY_WAVE6_LIVE=1" in live["detail"]


def test_assert_approval_slot_rejects_missing_or_local_only(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="missing"):
        assert_approval_slot_real_peers_uses_package(tmp_path)
    slot = tmp_path / "apps" / "web" / "src" / "slots" / "approval-slot.tsx"
    slot.parent.mkdir(parents=True)
    slot.write_text(
        'import { LocalApprovalSubstitute } from "./local-approval-substitute";\n'
        "export function ApprovalSlot() {\n"
        "  return <LocalApprovalSubstitute />;\n"
        "}\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match=APPROVAL_UI_EXPORT):
        assert_approval_slot_real_peers_uses_package(tmp_path)


def test_assert_approval_slot_passes_when_real_peers_uses_panel(tmp_path: Path) -> None:
    slot = tmp_path / "apps" / "web" / "src" / "slots" / "approval-slot.tsx"
    slot.parent.mkdir(parents=True)
    slot.write_text(
        f'import {{ {APPROVAL_UI_EXPORT} }} from "{APPROVAL_UI_PACKAGE_NAME}";\n'
        "export function ApprovalSlot() {\n"
        '  if (mode === "real-peers") {\n'
        f"    return <{APPROVAL_UI_EXPORT} />;\n"
        "  }\n"
        "  return <LocalApprovalSubstitute />;\n"
        "}\n",
        encoding="utf-8",
    )
    assert_approval_slot_real_peers_uses_package(tmp_path)

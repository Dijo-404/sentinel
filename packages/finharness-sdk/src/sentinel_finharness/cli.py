"""Local preview CLI. Fixture peers only; no network or sibling imports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import RuntimeConfig
from .contracts import CONTRACT_SHA256, CONTRACT_VERSION, PORT
from .manifest import CaseManifest
from .sample import run_sample_workflow


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_sample(args: argparse.Namespace) -> int:
    # Import stubs only from the tests tree when running inside the module checkout.
    stubs_dir = _package_root() / "tests" / "stubs"
    if str(stubs_dir.parent) not in sys.path:
        sys.path.insert(0, str(stubs_dir.parent))
    from stubs import (  # type: ignore[import-not-found]
        ValidActionLedger,
        ValidEvidence,
        ValidIndicContext,
        ValidPolicy,
        ValidVerifier,
    )

    if args.manifest:
        manifest_path = Path(args.manifest)
    else:
        manifest_path = _package_root() / "fixtures" / "case-manifest.json"
    manifest = CaseManifest.from_mapping(_load_json(manifest_path))
    config = RuntimeConfig.from_mapping(
        {
            "enabled": args.enabled,
            "execution_mode": args.mode,
            "financial_writes": args.financial_writes,
            "notifications": args.notifications,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )
    report = run_sample_workflow(
        config=config,
        manifest=manifest,
        evidence=ValidEvidence(),
        policy=ValidPolicy(),
        ledger=ValidActionLedger(),
        verifier=ValidVerifier(),
        indic_context=ValidIndicContext(),
        approval_id="synthetic-approval_id" if args.with_approval else None,
    )
    payload = {
        "contract_version": report.contract_version,
        "port": report.port,
        "baseline_sha256": report.baseline_sha256,
        "evidence_mode": report.evidence_mode,
        "workflow": report.workflow,
        "workflow_version": report.workflow_version,
        "routing_enabled": report.routing_enabled,
        "financial_writes": report.financial_writes,
        "notifications": report.notifications,
        "steps": list(report.steps),
        "policy_outcome": report.policy_outcome,
        "model_outcome": report.model_outcome,
        "action_id": report.action_id,
        "assessment_status": report.assessment_status,
        "defaults": {
            "contract_version": CONTRACT_VERSION,
            "port": PORT,
            "baseline_sha256": CONTRACT_SHA256,
            "enabled_default": False,
            "financial_writes_default": False,
            "notifications_default": False,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel-finharness")
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample", help="Run fixture sample workflow through the SDK")
    sample.add_argument("--manifest", default=None, help="Path to case manifest JSON")
    sample.add_argument("--enabled", action="store_true", help="Enable FinHarness routing")
    sample.add_argument(
        "--mode",
        choices=["legacy", "shadow", "harness"],
        default="legacy",
        help="Execution mode (default: legacy)",
    )
    sample.add_argument(
        "--financial-writes",
        action="store_true",
        help="Allow ledger proposal/reservation delegation",
    )
    sample.add_argument(
        "--notifications",
        action="store_true",
        help="Allow notification capability",
    )
    sample.add_argument(
        "--with-approval",
        action="store_true",
        help="Supply synthetic approval_id for reservation step",
    )
    sample.set_defaults(func=cmd_sample)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

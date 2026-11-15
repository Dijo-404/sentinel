"""CLI for release-evidence.v1 verification kit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinel_release_mvp.application.verify import (
    load_manifest,
    render_release_report,
    verify_manifest,
)
from sentinel_release_mvp.bootstrap import build_peers, contracts_dir, module_root
from sentinel_release_mvp.contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    ContractError,
    PeerError,
)
from sentinel_release_mvp.domain.procedures import procedure_checklist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sentinel-release-mvp",
        description="MVP release-evidence verification kit (not product release proof)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="Validate an evidence manifest")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--run-id", default="release-verify-1")
    verify.add_argument(
        "--strict-release",
        action="store_true",
        help="Require real-component evidence; fixture-only blocks approval",
    )
    verify.add_argument("--artifact-root", type=Path, default=None)
    verify.add_argument(
        "--with-peers",
        action="store_true",
        help="Exercise configured real-peer runners (never fixture-fallback)",
    )
    verify.add_argument("--json", action="store_true", help="Emit machine JSON")

    report = sub.add_parser("report", help="Render markdown report for a manifest")
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--run-id", default="release-report-1")
    report.add_argument("--strict-release", action="store_true")
    report.add_argument("--artifact-root", type=Path, default=None)

    proc = sub.add_parser("procedure", help="Print clean-checkout/demo procedure")
    proc.add_argument("--json", action="store_true")

    selftest = sub.add_parser(
        "self-test",
        help="Run positive/negative local manifests; exit 0 without claiming release",
    )
    selftest.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    try:
        if args.command == "procedure":
            steps = procedure_checklist()
            if args.json:
                print(json.dumps({"contract_version": CONTRACT_VERSION, "steps": steps}, indent=2))
            else:
                for step in steps:
                    print(f"## {step['id']}: {step['title']}")
                    print(f"  command: {step['command']}")
                    print(f"  expected: {step['expected']}")
                    print()
            return 0

        if args.command == "self-test":
            return _run_self_test(emit_json=args.json)

        mode = "real-peers" if args.strict_release else "fixture"
        peers = build_peers(mode=mode) if getattr(args, "with_peers", False) else None
        if args.command in {"verify", "report"}:
            manifest = load_manifest(args.manifest)
            run_report, verdict = verify_manifest(
                manifest,
                mode=mode,
                run_id=args.run_id,
                artifact_root=args.artifact_root,
                peers=peers,
            )
            if args.command == "report" or not getattr(args, "json", False):
                if args.command == "report":
                    print(render_release_report(run_report, verdict))
                else:
                    print(
                        json.dumps(
                            {
                                "run_report": run_report.to_dict(),
                                "verdict": verdict.to_dict(),
                                "baseline_sha256": CONTRACT_SHA256,
                            },
                            indent=2,
                        )
                    )
            else:
                print(
                    json.dumps(
                        {
                            "run_report": run_report.to_dict(),
                            "verdict": verdict.to_dict(),
                            "baseline_sha256": CONTRACT_SHA256,
                        },
                        indent=2,
                    )
                )
            if args.strict_release:
                return 0 if verdict.release_approved else 1
            # Fixture/self verify: PASS structural checks without release claim.
            return 0 if run_report.status == "PASS" else 1

    except (ContractError, PeerError) as exc:
        print(
            json.dumps(
                {
                    "code": getattr(exc, "code", "ERROR"),
                    "message": getattr(exc, "message", str(exc)),
                    "request_id": getattr(exc, "request_id", "request-local-1"),
                }
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    parser.error(f"unknown command {args.command}")
    return 2


def _run_self_test(*, emit_json: bool) -> int:
    root = contracts_dir() / "manifests"
    artifact_root = module_root() / "contracts" / "artifacts"
    cases = [
        ("positive-real.json", "real-peers", True, True),
        ("positive-fixture-selftest.json", "fixture", False, True),
        ("negative-missing-component.json", "real-peers", False, False),
        ("negative-failed-check.json", "real-peers", False, False),
        ("negative-incompatible-hash.json", "real-peers", False, False),
        ("negative-fixture-only.json", "real-peers", False, False),
    ]
    results = []
    for name, mode, expect_approved, expect_pass in cases:
        path = root / name
        manifest = load_manifest(path)
        report, verdict = verify_manifest(
            manifest,
            mode=mode,
            run_id=f"self-test:{name}",
            artifact_root=artifact_root if "positive-real" in name else None,
        )
        ok = (
            verdict.release_approved is expect_approved and (report.status == "PASS") is expect_pass
        )
        # Fixture self-test file: status PASS but never approved.
        if name == "positive-fixture-selftest.json":
            ok = report.status == "PASS" and verdict.release_approved is False
        results.append(
            {
                "manifest": name,
                "mode": mode,
                "status": report.status,
                "release_approved": verdict.release_approved,
                "reason_codes": list(verdict.reason_codes),
                "ok": ok,
            }
        )
    all_ok = all(r["ok"] for r in results)
    payload = {
        "contract_version": CONTRACT_VERSION,
        "baseline_sha256": CONTRACT_SHA256,
        "status": "PASS" if all_ok else "FAIL",
        "release_approved": False,
        "cases": results,
        "note": "Self-test PASS does not claim a product release.",
    }
    if emit_json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""CLI for fixture self-tests and strict real-peer assembly runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

from sentinel_core_assembly.adapters.composition import build_peers
from sentinel_core_assembly.adapters.config import AssemblyConfig
from sentinel_core_assembly.application.assembly import report_to_exit_code, run_assembly
from sentinel_core_assembly.domain.types import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    RunInput,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sentinel-core-assembly")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run local fixture self-tests (exit 0 on PASS)")
    check.add_argument("--run-id", default="")

    run = sub.add_parser("run", help="Run assembly in fixture or real-peers mode")
    run.add_argument("--mode", choices=("fixture", "real-peers"), default="")
    run.add_argument("--run-id", default="")
    run.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="kind,uri,sha256,component_version,evidence_mode",
    )

    caps = sub.add_parser("capabilities", help="Print core-assembly.v1 capabilities")
    caps.add_argument("--mode", choices=("fixture", "real-peers"), default="fixture")

    sub.add_parser(
        "seed-sandbox",
        help="Seed sandbox peer DBs (tenant-demo + SENTINEL_V1_SANDBOX only)",
    )
    sub.add_parser(
        "verify-wave0-1",
        help=(
            "HTTP 200 + seeded JSON from merchant-analytics metrics, "
            "merchant-disputes list, risk investigations (fails without seed)"
        ),
    )
    sub.add_parser(
        "verify-wave2",
        help=(
            "HTTP 200 + seeded JSON from case-api ops ESCALATED/HISTORY/messages/"
            "audit-events; optional identity /v1/ops/team when VERIFY_IDENTITY_TOKEN set"
        ),
    )
    sub.add_parser(
        "verify-wave3",
        help=(
            "HTTP 200 + seeded JSON from identity me/notifications/workspaces; "
            "forgot returns 202 without email enumeration (session via login or "
            "VERIFY_IDENTITY_TOKEN)"
        ),
    )
    sub.add_parser(
        "verify-wave4",
        help=(
            "HTTP 200 + seeded JSON from assistant threads, knowledge articles, "
            "ops-activity feed; voice /v1/capabilities; offline approval-ui package smoke"
        ),
    )
    sub.add_parser(
        "verify-wave5",
        help=(
            "HTTP 200 + seeded JSON from identity admin roles/tenants, policy policies, "
            "merchant-teams admin merchants, platform-ai config/integrations, evals "
            "reports, observability signals"
        ),
    )
    sub.add_parser(
        "verify-wave6",
        help=(
            "Portal stub scan + fixture assembly honesty + approval-ui ApprovalPanel "
            "smoke; optional VERIFY_WAVE6_LIVE=1 real-peers subset"
        ),
    )
    return parser.parse_args(argv)


def _artifacts(raw: list[str]) -> tuple[ArtifactRef, ...]:
    out: list[ArtifactRef] = []
    for item in raw:
        kind, uri, digest, version, evidence = item.split(",", 4)
        out.append(
            ArtifactRef(
                kind=kind,
                uri=uri,
                sha256=digest,
                component_version=version,
                evidence_mode=evidence,  # type: ignore[arg-type]
            )
        )
    return tuple(out)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = AssemblyConfig.from_env()

    if args.command == "capabilities":
        payload = {
            "contract_version": CONTRACT_VERSION,
            "component": "sentinel-core-assembly",
            "mode": args.mode,
            "port": PORT,
            "contract_sha256": CONTRACT_SHA256,
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if args.command == "seed-sandbox":
        from sentinel_core_assembly.adapters.seed_sandbox import seed_sandbox

        report = seed_sandbox(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave0-1":
        from sentinel_core_assembly.adapters.verify_wave0_1 import verify_wave0_1

        report = verify_wave0_1(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave2":
        from sentinel_core_assembly.adapters.verify_wave2 import verify_wave2

        report = verify_wave2(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave3":
        from sentinel_core_assembly.adapters.verify_wave3 import verify_wave3

        report = verify_wave3(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave4":
        from sentinel_core_assembly.adapters.verify_wave4 import verify_wave4

        report = verify_wave4(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave5":
        from sentinel_core_assembly.adapters.verify_wave5 import verify_wave5

        report = verify_wave5(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    if args.command == "verify-wave6":
        from sentinel_core_assembly.adapters.verify_wave6 import verify_wave6

        report = verify_wave6(dict(os.environ))
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report.get("status") == "PASS" else 1

    mode = getattr(args, "mode", "") or config.mode
    if args.command == "check":
        mode = "fixture"
    run_id = args.run_id or f"run-{uuid.uuid4().hex[:12]}"
    artifacts = _artifacts(getattr(args, "artifact", []) or [])
    run = RunInput(
        contract_version=CONTRACT_VERSION,
        run_id=run_id,
        mode=mode,  # type: ignore[arg-type]
        input_artifacts=artifacts,
        parameters={"component_version": "0.1.0"},
    )
    peers = build_peers(
        AssemblyConfig(
            mode=mode,
            contract_version=config.contract_version,
            contract_sha256=config.contract_sha256,
            peer_endpoints=config.peer_endpoints,
        )
    )
    report = run_assembly(run, peers)
    json.dump(report.as_dict(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return report_to_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())

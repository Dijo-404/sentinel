"""CLI for sandbox-validation.v1 kit runs."""

from __future__ import annotations

import argparse
import json
import sys

from sentinel_sandbox_pilot.adapters.composition import build_peers
from sentinel_sandbox_pilot.adapters.config import load_config
from sentinel_sandbox_pilot.application.validation import run_validation, self_check_report
from sentinel_sandbox_pilot.domain.types import CONTRACT_VERSION, RunInput


def _build_run(args: argparse.Namespace) -> RunInput:
    config = load_config()
    mode = args.mode or config.mode
    parameters: dict[str, str | int | bool] = {
        "component_version": "0.1.0",
        "sandbox_validation.external_authorization": (
            True if args.external_authorization else config.external_authorization
        ),
    }
    if args.claim_external_pilot:
        parameters["sandbox_validation.claim_external_pilot"] = True
    if args.fail_restore:
        parameters["sandbox_validation.fail_restore"] = True
    if args.drivers:
        parameters["drivers"] = args.drivers
    return RunInput(
        contract_version=CONTRACT_VERSION,
        run_id=args.run_id,
        mode=mode,
        parameters=parameters,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-sandbox-pilot")
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="module-local self-test (fixture peers only)")
    check_p.set_defaults(command="check")

    run_p = sub.add_parser("run", help="run sandbox-validation drivers")
    run_p.add_argument("--mode", choices=("fixture", "real-peers"), default=None)
    run_p.add_argument("--run-id", default="sandbox-pilot-run")
    run_p.add_argument("--drivers", default="")
    run_p.add_argument(
        "--external-authorization",
        action="store_true",
        help="owner-supplied external pilot authorization flag",
    )
    run_p.add_argument(
        "--claim-external-pilot",
        action="store_true",
        help="attempt to claim external pilot success (rejected without auth / in fixture)",
    )
    run_p.add_argument(
        "--fail-restore",
        action="store_true",
        help="force restore drill failure for negative testing",
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        report = self_check_report()
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0 if report.status == "PASS" else 1

    config = load_config()
    if args.mode:
        from dataclasses import replace

        config = replace(config, mode=args.mode)
    peers = build_peers(config)
    report = run_validation(_build_run(args), peers)
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if report.status in {"FAIL", "UNVERIFIED"} and args.mode == "real-peers":
        return 1
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

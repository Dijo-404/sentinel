from __future__ import annotations

import argparse
import json
import sys

from sentinel_harness_replay.application.service import compare_candidates, run_check
from sentinel_harness_replay.bootstrap import build_deps
from sentinel_harness_replay.fixtures import fixture_by_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-harness-replay")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run standalone self-check")
    check.set_defaults(func=_cmd_check)

    compare = sub.add_parser("compare", help="Compare bundled candidates with safety gate")
    compare.add_argument(
        "--fixture",
        default="bundled/dup_refund_timeout_001",
        help="Fixture id or bundled/<id>",
    )
    compare.set_defaults(func=_cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


def _cmd_check(_args: argparse.Namespace) -> int:
    report = run_check()
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == "PASS" else 1


def _cmd_compare(args: argparse.Namespace) -> int:
    fixture_token = args.fixture
    fixture_id = fixture_token.split("/", 1)[-1]
    mode, deps = build_deps()
    report = compare_candidates(
        fixture_by_id(fixture_id),
        run_id="harness-replay-cli-compare",
        mode=mode,
        deps=deps,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if mode == "fixture":
        return 0 if report.status == "PASS" else 1
    return 1 if report.status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())

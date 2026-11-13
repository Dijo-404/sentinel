"""CLI entry for fixture self-check and inspect helpers."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-finharness-runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-check", help="Run fixture-mode shadow/reconcile smoke")

    args = parser.parse_args(argv)
    if args.command == "self-check":
        from sentinel_finharness_runtime.application.runtime import self_check_report

        report = self_check_report()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("status") == "PASS" else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())

"""CLI entry for local preview helpers, sandbox seed, and workflow delivery."""

from __future__ import annotations

import argparse
import json
import os
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-api")
    parser.add_argument(
        "command",
        choices=["version", "contract", "flush-workflow", "seed"],
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="flush-workflow: single pass then exit (default for non-loop)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="flush-workflow: reclaim/deliver forever until interrupted",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="flush-workflow loop sleep seconds (default 2)",
    )
    args = parser.parse_args(argv)
    if args.command == "version":
        from sentinel_api import __version__

        print(__version__)
        return 0
    if args.command == "contract":
        from sentinel_api import CONTRACT_HASH, CONTRACT_VERSION

        print(f"{CONTRACT_VERSION} {CONTRACT_HASH}")
        return 0
    if args.command == "seed":
        from sentinel_api.adapters.seed import seed_ops_surfaces, seed_report_as_dict

        report = seed_ops_surfaces(os.environ)
        print(json.dumps(seed_report_as_dict(report)))
        return 0 if report["status"] == "PASS" else 2

    # flush-workflow: continuous reclaim of stale CLAIMED + PENDING delivery.
    from sentinel_api.bootstrap import build_app

    app = build_app()
    service = app.state.service
    if args.loop and not args.once:
        while True:
            n = service.flush_workflow()
            if n:
                print(f"delivered={n}", flush=True)
            time.sleep(max(args.interval, 0.1))
    n = service.flush_workflow()
    print(f"delivered={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

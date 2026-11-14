"""CLI entrypoint."""

from __future__ import annotations

import argparse
import os
import sys

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-refunds")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8029)

    args = parser.parse_args(argv)
    if args.command == "serve":
        from sentinel_merchant_refunds.adapters.auth import demo_principals
        from sentinel_merchant_refunds.adapters.bind_safety import (
            UnsafeBindError,
            assert_loopback_or_non_demo,
        )
        from sentinel_merchant_refunds.bootstrap import DEMO_BEARER_TOKEN

        tokens = list(demo_principals().keys())
        tokens.append(
            os.environ.get("MERCHANT_REFUNDS_PEER_BEARER_TOKEN")
            or os.environ.get("MERCHANT_REFUNDS_BEARER_TOKEN")
            or DEMO_BEARER_TOKEN
        )
        try:
            assert_loopback_or_non_demo(args.host, tokens)
        except UnsafeBindError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
        uvicorn.run(
            "sentinel_merchant_refunds.bootstrap:create_preview_app",
            factory=True,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()

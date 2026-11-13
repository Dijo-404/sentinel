"""CLI entrypoint."""

from __future__ import annotations

import argparse

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-refunds")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8029)

    args = parser.parse_args(argv)
    if args.command == "serve":
        uvicorn.run(
            "sentinel_merchant_refunds.bootstrap:create_preview_app",
            factory=True,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()

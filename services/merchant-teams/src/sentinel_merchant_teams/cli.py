"""Module CLI: serve merchant-teams.v1 and sandbox seed."""

from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .adapters.storage_postgres import seed_merchant_demo_membership
from .application.errors import ConfigurationError, TeamsError
from .bootstrap import Settings, build_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-teams")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run merchant-teams.v1 HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8034)
    sub.add_parser(
        "seed",
        help="Migrate + seed synthetic merchant-demo-1 membership into Postgres",
    )

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "serve":
            tokens = list(parse_token_map(settings.tokens).keys())
            if settings.case_api_token:
                tokens.append(settings.case_api_token)
            try:
                assert_loopback_or_non_demo(args.host, tokens)
            except UnsafeBindError as exc:
                print(f'{{"code":"UNSAFE_BIND","message":"{exc}"}}', file=sys.stderr)
                return 2
            app = build_app(settings)
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
        if args.command == "seed":
            if not settings.database_url.strip():
                raise ConfigurationError("MERCHANT_TEAMS_DATABASE_URL is required for seed")
            report = seed_merchant_demo_membership(settings.database_url)
            print(json.dumps(report, sort_keys=True))
            return 0
    except TeamsError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Module CLI: serve and seed risk.v1."""

from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .application.errors import ConfigurationError, RiskError
from .bootstrap import Settings, build_app
from .seed import seed_demo_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-risk")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run risk.v1 HTTP service")
    serve.add_argument("--host", default=os.environ.get("RISK_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("RISK_PORT", "8013")))
    sub.add_parser(
        "seed",
        help=(
            "Write sandbox investigation/restriction/findings for "
            "case-demo-42 (requires RISK_DATABASE_URL)"
        ),
    )

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "serve":
            tokens = list(parse_token_map(settings.tokens).keys())
            for attr in ("case_api_token", "workflow_token"):
                value = getattr(settings, attr, "") or ""
                if value:
                    tokens.append(value)
            try:
                assert_loopback_or_non_demo(args.host, tokens)
            except UnsafeBindError as exc:
                print(f'{{"code":"UNSAFE_BIND","message":"{exc}"}}', file=sys.stderr)
                return 2
            app = build_app(settings)
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
        if args.command == "seed":
            report = seed_demo_case(settings.database_url)
            print(json.dumps(report))
            return 0
    except RiskError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

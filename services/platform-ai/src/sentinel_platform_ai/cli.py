"""Module CLI: serve and seed platform-ai.v1."""

from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .application.errors import ConfigurationError, PlatformAiError
from .bootstrap import Settings, build_app
from .seed import seed_demo_platform_ai


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-platform-ai")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run platform-ai.v1 HTTP service")
    serve.add_argument("--host", default=os.environ.get("PLATFORM_AI_HOST", "127.0.0.1"))
    serve.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PLATFORM_AI_PORT", "8036")),
    )

    sub.add_parser(
        "seed",
        help="Write one sandbox AI config + run for tenant-demo (requires DATABASE_URL)",
    )

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "serve":
            tokens = list(parse_token_map(settings.tokens).keys())
            try:
                assert_loopback_or_non_demo(args.host, tokens)
            except UnsafeBindError as exc:
                print(f'{{"code":"UNSAFE_BIND","message":"{exc}"}}', file=sys.stderr)
                return 2
            app = build_app(settings)
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
        if args.command == "seed":
            report = seed_demo_platform_ai(settings.database_url)
            print(json.dumps(report))
            return 0 if report.get("status") == "PASS" else 1
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    except PlatformAiError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

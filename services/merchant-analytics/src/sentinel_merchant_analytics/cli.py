"""Module CLI: serve and seed merchant-analytics.v1."""

from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .application.errors import AnalyticsError, ConfigurationError
from .bootstrap import Settings, build_app
from .seed import seed_demo_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-analytics")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run merchant-analytics.v1 HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8032)

    sub.add_parser(
        "seed",
        help="Write one sandbox metrics snapshot for merchant-demo-1 (requires DATABASE_URL)",
    )

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "serve":
            tokens = list(parse_token_map(settings.tokens).keys())
            for attr in ("case_api_token", "evidence_token"):
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
            metrics = seed_demo_snapshot(settings.database_url)
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "peer": "merchant-analytics",
                        "rows": 1,
                        "merchant_ref": metrics.merchant_ref,
                        "window_start": metrics.window_start,
                        "window_end": metrics.window_end,
                    }
                )
            )
            return 0
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    except AnalyticsError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

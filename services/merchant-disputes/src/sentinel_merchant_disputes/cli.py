"""Module CLI: serve, migrate, and sandbox seed for merchant-disputes.v1."""

from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .adapters.seed import seed_report_as_dict, seed_sandbox_dispute
from .adapters.storage_postgres import PostgresDisputeStore, build_engine
from .application.errors import ConfigurationError, DisputeError
from .bootstrap import Settings, build_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-disputes")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run merchant-disputes.v1 HTTP service")
    serve.add_argument("--host", default=os.environ.get("DISPUTES_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("DISPUTES_PORT", "8030")))
    sub.add_parser("migrate", help="Apply owned PostgreSQL schema")
    sub.add_parser("seed", help="Seed one OPEN dispute for tenant-demo (sandbox only)")

    args = parser.parse_args(argv)
    try:
        if args.command == "migrate":
            database_url = os.environ.get("DISPUTES_DATABASE_URL", "")
            if not database_url.startswith("postgresql"):
                msg = "DISPUTES_DATABASE_URL PostgreSQL required"
                print(f'{{"code":"CONFIGURATION","message":"{msg}"}}', file=sys.stderr)
                return 2
            store = PostgresDisputeStore(build_engine(database_url))
            store.migrate()
            print('{"status":"ok","schema":"merchant_disputes"}')
            return 0
        if args.command == "seed":
            report = seed_sandbox_dispute(os.environ)
            print(json.dumps(seed_report_as_dict(report)))
            return 0 if report["status"] == "PASS" else 2
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
    except DisputeError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

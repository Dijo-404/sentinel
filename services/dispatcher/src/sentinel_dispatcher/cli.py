"""CLI: capabilities, migrate, run-once, recover."""

from __future__ import annotations

import argparse
import json
import os
import sys

from sqlalchemy import create_engine

from sentinel_dispatcher.adapters.postgres_store import ensure_schema
from sentinel_dispatcher.composition import build_real_peer_app_from_env, capabilities


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-dispatcher")
    sub = parser.add_subparsers(dest="command", required=True)

    caps = sub.add_parser("capabilities", help="Emit dispatcher.v1 capabilities")
    caps.add_argument("--mode", default=os.environ.get("DISPATCHER_MODE", "fixture"))

    migrate = sub.add_parser("migrate", help="Apply dispatcher schema to DATABASE_URL")
    migrate.add_argument(
        "--schema",
        default=os.environ.get("DISPATCHER_SCHEMA", "dispatcher"),
    )

    sub.add_parser("run-once", help="Claim and process one batch (real-peer mode)")
    sub.add_parser("recover", help="Reconcile incomplete durable jobs (real-peer mode)")

    args = parser.parse_args(argv)
    if args.command == "capabilities":
        print(json.dumps(capabilities(mode=args.mode), sort_keys=True))
        return 0
    if args.command == "migrate":
        url = os.environ.get("DATABASE_URL")
        if not url:
            print("DATABASE_URL is required", file=sys.stderr)
            return 2
        engine = create_engine(url, hide_parameters=True)
        try:
            ensure_schema(engine, args.schema)
        finally:
            engine.dispose()
        print(json.dumps({"migrated": True, "schema": args.schema}))
        return 0
    if args.command in {"run-once", "recover"}:
        app = build_real_peer_app_from_env()
        try:
            if args.command == "run-once":
                result = app.worker.run_once(limit=10)
            else:
                result = app.worker.recover()
            print(json.dumps({"results": result}, sort_keys=True))
            return 0
        finally:
            app.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

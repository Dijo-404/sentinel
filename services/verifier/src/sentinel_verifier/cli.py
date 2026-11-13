"""Module CLI: capabilities and migrate helpers."""

from __future__ import annotations

import argparse
import json
import os
import sys

from sqlalchemy import create_engine

from sentinel_verifier import COMPONENT, CONTRACT_SHA256, CONTRACT_VERSION, __version__
from sentinel_verifier.adapters.postgres_store import ensure_schema


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-verifier")
    sub = parser.add_subparsers(dest="command", required=True)

    caps = sub.add_parser("capabilities", help="Print verifier.v1 capabilities JSON")
    caps.add_argument("--mode", default=os.environ.get("VERIFIER_MODE", "fixture"))

    migrate = sub.add_parser("migrate", help="Apply owned schema DDL")
    migrate.add_argument(
        "--schema",
        default=os.environ.get("VERIFIER_SCHEMA", "verifier"),
    )

    args = parser.parse_args(argv)
    if args.command == "capabilities":
        payload = {
            "contract_version": CONTRACT_VERSION,
            "component": COMPONENT,
            "mode": args.mode,
            "port": "verifier.v1",
            "contract_sha256": CONTRACT_SHA256,
            "version": __version__,
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0
    if args.command == "migrate":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            sys.stderr.write("DATABASE_URL required\n")
            return 2
        engine = create_engine(database_url, hide_parameters=True)
        ensure_schema(engine, args.schema)
        engine.dispose()
        sys.stdout.write(f"schema={args.schema} applied\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Module CLI: migrate and serve."""

from __future__ import annotations

import argparse
import sys

import uvicorn
from sqlalchemy import create_engine

from .adapters.storage_postgres import PostgresEvidenceStore
from .application.errors import ConfigurationError, EvidenceError
from .bootstrap import Settings, build_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Create evidence schema/tables")
    serve = sub.add_parser("serve", help="Run evidence.v1 HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8006)

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "migrate":
            if not settings.database_url:
                raise ConfigurationError("DATABASE_URL is required for migrate")
            engine = create_engine(settings.database_url, hide_parameters=True)
            PostgresEvidenceStore(engine, schema=settings.schema).migrate()
            print(f'{{"status":"migrated","schema":"{settings.schema}"}}')
            return 0
        if args.command == "serve":
            app = build_app(settings)
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
    except EvidenceError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

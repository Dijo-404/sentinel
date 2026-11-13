"""CLI entrypoints for migrate/serve."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Apply module-owned schema")
    serve = sub.add_parser("serve", help="Run workflow HTTP API")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    args = parser.parse_args(argv)
    if args.command == "migrate":
        from sentinel_workflow.adapters.db import make_engine, migrate
        from sentinel_workflow.adapters.settings import Settings

        settings = Settings()
        migrate(make_engine(settings.database_url))
        print("workflow schema ready")
        return 0

    if args.command == "serve":
        import uvicorn

        from sentinel_workflow.bootstrap import build_container

        container = build_container()
        host = args.host or container.settings.host
        port = args.port or container.settings.port
        uvicorn.run(container.app, host=host, port=port)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

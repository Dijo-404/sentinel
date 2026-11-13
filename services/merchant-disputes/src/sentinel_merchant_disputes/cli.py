"""Module CLI: serve merchant-disputes.v1."""

from __future__ import annotations

import argparse
import os

import uvicorn

from .application.errors import ConfigurationError, DisputeError
from .bootstrap import Settings, build_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-disputes")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run merchant-disputes.v1 HTTP service")
    serve.add_argument("--host", default=os.environ.get("DISPUTES_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("DISPUTES_PORT", "8030")))

    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.command == "serve":
            app = build_app(settings)
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0
    except DisputeError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=__import__("sys").stderr)
        return 2
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=__import__("sys").stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

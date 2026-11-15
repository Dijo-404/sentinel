"""Module CLI: `sentinel-model-gateway serve --host --port`."""

from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from .application.errors import ConfigurationError
from .bootstrap import Settings, build_app

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
DEMO_TOKENS = frozenset({"tok-workflow", "workflow-token", "tok-case-api", "case-api-token"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-model-gateway")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run the Sarvam-backed model gateway")
    serve.add_argument("--host", default=os.environ.get("MODEL_GATEWAY_HOST", "127.0.0.1"))
    serve.add_argument(
        "--port", type=int, default=int(os.environ.get("MODEL_GATEWAY_PORT", "8040"))
    )
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_environ()
        demo = sorted(settings.proposal_tokens & DEMO_TOKENS)
        if args.host.strip().lower() not in _LOOPBACK and demo:
            raise ConfigurationError(
                f"Refusing non-loopback bind {args.host!r} with demo bearer tokens: "
                f"{', '.join(demo)}"
            )
        app = build_app(settings)
    except ConfigurationError as exc:
        print(json.dumps({"code": exc.code, "message": exc.message}), file=sys.stderr)
        return 2
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

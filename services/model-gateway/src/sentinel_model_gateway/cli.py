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


def assert_safe_bind(host: str, settings: Settings) -> None:
    """Non-loopback needs non-demo tokens and reply tokens (else /v1/replies is open)."""
    if host.strip().lower() in _LOOPBACK:
        return
    demo = sorted((settings.proposal_tokens | settings.reply_tokens) & DEMO_TOKENS)
    if demo:
        raise ConfigurationError(
            f"Refusing non-loopback bind {host!r} with demo bearer tokens: {', '.join(demo)}"
        )
    if not settings.reply_tokens:
        raise ConfigurationError(
            f"Refusing non-loopback bind {host!r}: set MODEL_GATEWAY_REPLY_TOKENS so "
            "/v1/replies requires a bearer token"
        )


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
        assert_safe_bind(args.host, settings)
        app = build_app(settings)
    except ConfigurationError as exc:
        print(json.dumps({"code": exc.code, "message": exc.message}), file=sys.stderr)
        return 2
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

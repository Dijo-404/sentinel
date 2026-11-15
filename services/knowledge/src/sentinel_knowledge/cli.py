"""Module CLI: serve and seed knowledge.v1."""

from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from .adapters.auth import parse_token_map
from .adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from .application.errors import ConfigurationError, KnowledgeError
from .bootstrap import Settings, build_app, build_postgres_store
from .seed import seed_demo_articles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-knowledge")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run knowledge.v1 HTTP service")
    serve.add_argument("--host", default=os.environ.get("KNOWLEDGE_HOST", "127.0.0.1"))
    serve.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("KNOWLEDGE_PORT", "8035")),
    )
    sub.add_parser(
        "seed",
        help=("Write sandbox knowledge article for tenant-demo (requires KNOWLEDGE_DATABASE_URL)"),
    )
    reindex = sub.add_parser(
        "reindex",
        help="Migrate pgvector schema and embed rows missing a vector for the active model",
    )
    reindex.add_argument("--all", action="store_true", help="Re-embed every row")

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
            report = seed_demo_articles(settings.database_url)
            print(json.dumps(report))
            return 0
        if args.command == "reindex":
            store = build_postgres_store(settings, reset_dimension=True)
            rows = store.reindex(force=args.all)
            print(
                json.dumps(
                    {"status": "PASS", "model": settings.embedding_model, "rows_embedded": rows}
                )
            )
            return 0
    except KnowledgeError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    except ConfigurationError as exc:
        print(f'{{"code":"{exc.code}","message":"{exc.message}"}}', file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

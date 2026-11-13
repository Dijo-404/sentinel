"""CLI: serve HTTP adapter or print a labeled fake inference report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from sentinel_indic_context.adapters.settings import Settings
from sentinel_indic_context.bootstrap import build_app, build_service
from sentinel_indic_context.domain.types import ModelRequest, Principal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-indic-context")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Serve POST /v1/proposals")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    preview = sub.add_parser("preview", help="Run one fake proposal against a fixture")
    preview.add_argument(
        "--fixture",
        default=str(Path(__file__).resolve().parents[2] / "fixtures" / "tamil_duplicate.json"),
    )

    args = parser.parse_args(argv)
    settings = Settings()

    if args.command == "serve":
        app = build_app(settings)
        uvicorn.run(
            app,
            host=args.host or settings.host,
            port=args.port or settings.port,
        )
        return 0

    if args.command == "preview":
        if settings.mode != "fake":
            print("preview uses fake mode only; set INDIC_CONTEXT_MODE=fake", file=sys.stderr)
            return 2
        service = build_service(settings)
        payload = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        request = ModelRequest.model_validate(payload["request"])
        principal = Principal.model_validate(payload["principal"])
        result, report, normalized = service.propose(request, principal)
        print(
            json.dumps(
                {
                    "result": result.model_dump(exclude_none=True),
                    "inference_report": report.model_dump(exclude_none=True),
                    "normalized": normalized.model_dump(exclude_none=True),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

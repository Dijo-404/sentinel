"""CLI: serve HTTP adapter or preview one draft lifecycle."""

from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from sentinel_merchant_comms.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)
from sentinel_merchant_comms.adapters.settings import Settings
from sentinel_merchant_comms.bootstrap import build_app, build_service
from sentinel_merchant_comms.domain.types import Principal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentinel-merchant-comms")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Serve merchant-comms.v1 HTTP API")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    preview = sub.add_parser("preview", help="Create/approve/simulate one labeled draft")
    preview.add_argument("--case-id", default="case-demo-42")
    preview.add_argument("--language", choices=["en", "ta", "hi"], default="en")
    preview.add_argument("--no-indic", action="store_true")

    args = parser.parse_args(argv)
    settings = Settings()

    if args.command == "serve":
        host = args.host or settings.host
        tokens = list(settings.token_map_raw().keys())
        for value in (settings.case_api_token, settings.indic_context_token):
            if value:
                tokens.append(value)
        try:
            assert_loopback_or_non_demo(host, tokens)
        except UnsafeBindError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        app = build_app(settings)
        uvicorn.run(
            app,
            host=host,
            port=args.port or settings.port,
        )
        return 0

    if args.command == "preview":
        service = build_service(settings, use_indic=not args.no_indic)
        principal = Principal(
            principal_id="op-demo",
            tenant_id="tenant-demo",
            roles=["operator"],
            subject_refs=["subject-demo"],
            case_ids=[args.case_id],
        )
        draft = service.create_draft(
            case_id=args.case_id, language=args.language, principal=principal
        )
        approved = service.decide(draft_id=draft.draft_id, decision="APPROVE", principal=principal)
        sent = service.simulate_send(draft_id=approved.draft_id, principal=principal)
        json.dump(sent.model_dump(exclude_none=True), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    return 1

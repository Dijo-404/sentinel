"""Run the merchant SLA HTTP service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from sentinel_merchant_sla.adapters.auth import TokenMap
from sentinel_merchant_sla.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from sentinel_merchant_sla.bootstrap import DEFAULT_PRINCIPALS, build_app


def main() -> None:
    host = os.environ.get("MERCHANT_SLA_HOST", "127.0.0.1")
    port = int(os.environ.get("MERCHANT_SLA_PORT", "8031"))
    path = Path(os.environ.get("MERCHANT_SLA_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = list(TokenMap.from_path(path).tokens.keys())
    peer = os.environ.get("MERCHANT_SLA_CASE_API_TOKEN", "")
    if peer:
        tokens.append(peer)
    try:
        assert_loopback_or_non_demo(host, tokens)
    except UnsafeBindError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

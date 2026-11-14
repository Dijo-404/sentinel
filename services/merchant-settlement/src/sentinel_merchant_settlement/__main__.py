"""Run the merchant settlement HTTP service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from sentinel_merchant_settlement.adapters.auth import TokenMap
from sentinel_merchant_settlement.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)
from sentinel_merchant_settlement.bootstrap import DEFAULT_PRINCIPALS, build_app


def main() -> None:
    host = os.environ.get("MERCHANT_SETTLEMENT_HOST", "127.0.0.1")
    port = int(os.environ.get("MERCHANT_SETTLEMENT_PORT", "8027"))
    path = Path(os.environ.get("MERCHANT_SETTLEMENT_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = list(TokenMap.from_path(path).tokens.keys())
    for key in ("EVIDENCE_TOKEN", "PAYMENT_PROVIDER_TOKEN"):
        value = os.environ.get(key, "")
        if value:
            tokens.append(value)
    try:
        assert_loopback_or_non_demo(host, tokens)
    except UnsafeBindError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    app = build_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
